/*
 * iotbench-simd - shared IoT peripheral simulator.
 *
 * Reads a peripheral spec (default /etc/iotbench/peripherals.conf) and writes
 * live, realistically varying values every interval seconds to:
 *   - /run/iotbench/state.json  (JSON, consumed by the web admin)
 *   - /run/iotbench/state.env   (flat NAME=value lines, for shell/C services)
 * Device skeletons expose the values over their native protocol (HTTP, MQTT,
 * Modbus, MJPEG...).
 *
 * Value models (grounded in standard stochastic-process methods used for
 * synthetic sensor/telemetry generation):
 *   walk/walkint  Ornstein-Uhlenbeck mean-reverting process (Uhlenbeck & Ornstein,
 *                 Phys. Rev. 36, 1930): dx = theta*(mu-x)*dt + sigma*sqrt(dt)*N(0,1),
 *                 clamped to [min,max]. Realistic bounded sensor drift.
 *                 Keys: mu (mean, default init/midpoint), theta (reversion rate),
 *                 step (sigma, volatility), min, max, init, unit.
 *   diurnal       seasonal mean + noise: base + amp*sin(2pi*t/period) + N(0,noise).
 *   binary        two-state (random telegraph) Markov process: p01, p10.
 *   enum          finite-state Markov jump process: states=a,b,c, jump prob p.
 *   counter       monotonic accumulator (e.g. energy): rate per second.
 */
#define _POSIX_C_SOURCE 200809L
#include <math.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

#define MAX_PERIPHERALS 64
#define MAX_STATES 12
#define NAME_LEN 48
#define UNIT_LEN 16
#define STATE_LEN 24

enum ptype { P_WALK, P_WALKINT, P_DIURNAL, P_BINARY, P_ENUM, P_COUNTER, P_DERIVED };

/* Correlation operators for P_DERIVED (value computed from other peripherals). */
enum dop { D_SCALE, D_DIV, D_MUL, D_ADD, D_SUB, D_GATE, D_INTEGRATE };

struct peripheral {
    char name[NAME_LEN];
    char unit[UNIT_LEN];
    enum ptype type;
    double val;            /* current numeric value */
    double min, max;
    double mu, theta, step;/* OU mean, reversion rate, volatility (sigma) */
    double base, amp, noise;
    long period;           /* diurnal */
    double rate;           /* counter, per second */
    double p01, p10, p;    /* binary / enum transition probabilities */
    char states[MAX_STATES][STATE_LEN];
    int nstates, state_idx;
    /* derived: value = op(a, b, k) of other peripherals, evaluated each tick */
    enum dop op;
    double k;
    char ref_a[NAME_LEN], ref_b[NAME_LEN];
    int idx_a, idx_b;
};

static struct peripheral peripherals[MAX_PERIPHERALS];
static int n_peripherals;
static volatile sig_atomic_t running = 1;

static void on_signal(int sig) { (void)sig; running = 0; }

/* Standard normal via Box-Muller. */
static double gauss(void)
{
    double u1 = (rand() + 1.0) / (RAND_MAX + 2.0);
    double u2 = (rand() + 1.0) / (RAND_MAX + 2.0);
    return sqrt(-2.0 * log(u1)) * cos(2.0 * M_PI * u2);
}

static double frand(void) { return rand() / (RAND_MAX + 1.0); }

static double clampd(double v, double lo, double hi)
{
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

static enum ptype parse_type(const char *s)
{
    if (!strcmp(s, "walk")) return P_WALK;
    if (!strcmp(s, "walkint")) return P_WALKINT;
    if (!strcmp(s, "diurnal")) return P_DIURNAL;
    if (!strcmp(s, "binary")) return P_BINARY;
    if (!strcmp(s, "enum")) return P_ENUM;
    if (!strcmp(s, "counter")) return P_COUNTER;
    if (!strcmp(s, "derived")) return P_DERIVED;
    return P_WALK;
}

static enum dop parse_op(const char *s)
{
    if (!strcmp(s, "div")) return D_DIV;
    if (!strcmp(s, "mul")) return D_MUL;
    if (!strcmp(s, "add")) return D_ADD;
    if (!strcmp(s, "sub")) return D_SUB;
    if (!strcmp(s, "gate")) return D_GATE;
    if (!strcmp(s, "integrate")) return D_INTEGRATE;
    return D_SCALE;
}

static void parse_states(struct peripheral *p, const char *csv)
{
    p->nstates = 0;
    const char *start = csv;
    while (*start && p->nstates < MAX_STATES) {
        const char *comma = strchr(start, ',');
        size_t len = comma ? (size_t)(comma - start) : strlen(start);
        if (len >= STATE_LEN) len = STATE_LEN - 1;
        memcpy(p->states[p->nstates], start, len);
        p->states[p->nstates][len] = '\0';
        p->nstates++;
        if (!comma) break;
        start = comma + 1;
    }
}

static int load_spec(const char *path)
{
    FILE *f = fopen(path, "r");
    if (!f) {
        fprintf(stderr, "iotbench-simd: cannot open %s\n", path);
        return -1;
    }
    char line[512];
    while (fgets(line, sizeof(line), f) && n_peripherals < MAX_PERIPHERALS) {
        char *hash = strchr(line, '#');
        if (hash) *hash = '\0';
        char *tok = strtok(line, " \t\r\n");
        if (!tok) continue;
        struct peripheral *p = &peripherals[n_peripherals];
        memset(p, 0, sizeof(*p));
        snprintf(p->name, sizeof(p->name), "%s", tok);
        tok = strtok(NULL, " \t\r\n");
        if (!tok) continue;
        p->type = parse_type(tok);
        /* defaults */
        p->step = 1.0; p->max = 100.0; p->min = 0.0; p->period = 86400;
        p->p01 = 0.05; p->p10 = 0.05; p->p = 0.05; p->rate = 0.0;
        p->theta = 0.05; p->k = 1.0; p->idx_a = -1; p->idx_b = -1;
        if (p->type == P_DERIVED) { p->min = -1e18; p->max = 1e18; }
        int have_init = 0, have_mu = 0;
        char *kv;
        while ((kv = strtok(NULL, " \t\r\n")) != NULL) {
            char *eq = strchr(kv, '=');
            if (!eq) continue;
            *eq = '\0';
            const char *key = kv, *val = eq + 1;
            if (!strcmp(key, "unit")) snprintf(p->unit, sizeof(p->unit), "%s", val);
            else if (!strcmp(key, "min")) p->min = atof(val);
            else if (!strcmp(key, "max")) p->max = atof(val);
            else if (!strcmp(key, "step")) p->step = atof(val);
            else if (!strcmp(key, "mu")) { p->mu = atof(val); have_mu = 1; }
            else if (!strcmp(key, "theta")) p->theta = atof(val);
            else if (!strcmp(key, "base")) p->base = atof(val);
            else if (!strcmp(key, "amp")) p->amp = atof(val);
            else if (!strcmp(key, "noise")) p->noise = atof(val);
            else if (!strcmp(key, "period")) p->period = atol(val);
            else if (!strcmp(key, "rate")) p->rate = atof(val);
            else if (!strcmp(key, "p01")) p->p01 = atof(val);
            else if (!strcmp(key, "p10")) p->p10 = atof(val);
            else if (!strcmp(key, "p")) p->p = atof(val);
            else if (!strcmp(key, "states")) parse_states(p, val);
            else if (!strcmp(key, "op")) p->op = parse_op(val);
            else if (!strcmp(key, "a")) snprintf(p->ref_a, sizeof(p->ref_a), "%s", val);
            else if (!strcmp(key, "b")) snprintf(p->ref_b, sizeof(p->ref_b), "%s", val);
            else if (!strcmp(key, "k")) p->k = atof(val);
            else if (!strcmp(key, "init")) { p->val = atof(val); have_init = 1; }
        }
        if (p->type == P_ENUM) {
            if (p->nstates == 0) { snprintf(p->states[0], STATE_LEN, "on"); p->nstates = 1; }
            if (have_init) {
                for (int i = 0; i < p->nstates; i++)
                    if ((int)p->val == i) p->state_idx = i;
            }
        }
        if (!have_init && (p->type == P_WALK || p->type == P_WALKINT))
            p->val = (p->min + p->max) / 2.0;
        /* OU mean defaults to the initial value, else the midpoint. */
        if (!have_mu)
            p->mu = have_init ? p->val : (p->min + p->max) / 2.0;
        n_peripherals++;
    }
    fclose(f);
    return n_peripherals;
}

static int find_index(const char *name)
{
    for (int i = 0; i < n_peripherals; i++)
        if (!strcmp(peripherals[i].name, name)) return i;
    return -1;
}

/* Link derived peripherals to the ones they reference (by name). */
static void resolve_derived(void)
{
    for (int i = 0; i < n_peripherals; i++) {
        if (peripherals[i].type != P_DERIVED) continue;
        if (peripherals[i].ref_a[0]) peripherals[i].idx_a = find_index(peripherals[i].ref_a);
        if (peripherals[i].ref_b[0]) peripherals[i].idx_b = find_index(peripherals[i].ref_b);
    }
}

static void step_peripheral(struct peripheral *p, long now, double dt)
{
    switch (p->type) {
    case P_DERIVED: {
        double a = p->idx_a >= 0 ? peripherals[p->idx_a].val : 0.0;
        double b = p->idx_b >= 0 ? peripherals[p->idx_b].val : 0.0;
        switch (p->op) {
        case D_DIV:       p->val = (b != 0.0) ? a / b : 0.0; break;
        case D_MUL:       p->val = a * b; break;
        case D_ADD:       p->val = a + b; break;
        case D_SUB:       p->val = a - b; break;
        case D_GATE:      p->val = (a >= 0.5) ? p->k : 0.0; break;
        case D_INTEGRATE: p->val += a * dt / (p->k != 0.0 ? p->k : 1.0); break;
        case D_SCALE:     default: p->val = p->k * a; break;
        }
        p->val = clampd(p->val, p->min, p->max);
        break;
    }
    case P_WALK:
    case P_WALKINT:
        /* Ornstein-Uhlenbeck: mean-reverting drift + volatility. */
        p->val += p->theta * (p->mu - p->val) * dt + p->step * sqrt(dt) * gauss();
        p->val = clampd(p->val, p->min, p->max);
        if (p->type == P_WALKINT)
            p->val = (double)((long)(p->val + (p->val >= 0 ? 0.5 : -0.5)));
        break;
    case P_DIURNAL:
        p->val = p->base + p->amp * sin(2.0 * M_PI * ((double)(now % p->period)) / (double)p->period)
                 + p->noise * gauss();
        break;
    case P_BINARY:
        if (p->val >= 0.5) { if (frand() < p->p10) p->val = 0.0; }
        else { if (frand() < p->p01) p->val = 1.0; }
        break;
    case P_ENUM:
        if (p->nstates > 1 && frand() < p->p) {
            int next = rand() % p->nstates;
            if (next == p->state_idx) next = (next + 1) % p->nstates;
            p->state_idx = next;
        }
        break;
    case P_COUNTER:
        p->val += p->rate * dt;
        break;
    }
}

static int write_json(const char *path, long now)
{
    char tmp[512];
    snprintf(tmp, sizeof(tmp), "%s.tmp", path);
    FILE *f = fopen(tmp, "w");
    if (!f) return -1;
    fprintf(f, "{\"ts\":%ld,\"peripherals\":{", now);
    for (int i = 0; i < n_peripherals; i++) {
        struct peripheral *p = &peripherals[i];
        fprintf(f, "%s\"%s\":{\"value\":", i ? "," : "", p->name);
        if (p->type == P_ENUM) fprintf(f, "\"%s\"", p->states[p->state_idx]);
        else if (p->type == P_WALKINT || p->type == P_BINARY) fprintf(f, "%ld", (long)p->val);
        else fprintf(f, "%.2f", p->val);
        fprintf(f, ",\"unit\":\"%s\"}", p->unit);
    }
    fprintf(f, "}}\n");
    fclose(f);
    return rename(tmp, path);
}

static int write_env(const char *path, long now)
{
    char tmp[512];
    snprintf(tmp, sizeof(tmp), "%s.tmp", path);
    FILE *f = fopen(tmp, "w");
    if (!f) return -1;
    fprintf(f, "TS=%ld\n", now);
    for (int i = 0; i < n_peripherals; i++) {
        struct peripheral *p = &peripherals[i];
        if (p->type == P_ENUM) fprintf(f, "%s=%s\n", p->name, p->states[p->state_idx]);
        else if (p->type == P_WALKINT || p->type == P_BINARY) fprintf(f, "%s=%ld\n", p->name, (long)p->val);
        else fprintf(f, "%s=%.2f\n", p->name, p->val);
    }
    fclose(f);
    return rename(tmp, path);
}

static void ensure_parent_dir(const char *path)
{
    char dir[512];
    snprintf(dir, sizeof(dir), "%s", path);
    char *slash = strrchr(dir, '/');
    if (slash && slash != dir) {
        *slash = '\0';
        mkdir(dir, 0755); /* best effort */
    }
}

int main(int argc, char **argv)
{
    const char *spec = "/etc/iotbench/peripherals.conf";
    const char *out_json = "/run/iotbench/state.json";
    const char *out_env = "/run/iotbench/state.env";
    int interval = 5;
    const char *env;

    if ((env = getenv("IOTBENCH_SIM_SPEC"))) spec = env;
    if ((env = getenv("IOTBENCH_SIM_STATE"))) out_json = env;
    if ((env = getenv("IOTBENCH_SIM_ENV"))) out_env = env;
    if ((env = getenv("IOTBENCH_SIM_INTERVAL"))) interval = atoi(env);
    if (argc > 1) spec = argv[1];
    if (argc > 2) out_json = argv[2];
    if (interval < 1) interval = 1;

    signal(SIGTERM, on_signal);
    signal(SIGINT, on_signal);
    srand((unsigned)(time(NULL) ^ getpid()));

    if (load_spec(spec) <= 0) {
        fprintf(stderr, "iotbench-simd: no peripherals loaded from %s\n", spec);
        return 1;
    }
    resolve_derived();
    ensure_parent_dir(out_json);
    ensure_parent_dir(out_env);

    while (running) {
        long now = (long)time(NULL);
        /* Step primaries first, then derived (which read the fresh values). */
        for (int i = 0; i < n_peripherals; i++)
            if (peripherals[i].type != P_DERIVED)
                step_peripheral(&peripherals[i], now, (double)interval);
        for (int i = 0; i < n_peripherals; i++)
            if (peripherals[i].type == P_DERIVED)
                step_peripheral(&peripherals[i], now, (double)interval);
        write_json(out_json, now);
        write_env(out_env, now);
        for (int s = 0; s < interval && running; s++)
            sleep(1);
    }
    return 0;
}
