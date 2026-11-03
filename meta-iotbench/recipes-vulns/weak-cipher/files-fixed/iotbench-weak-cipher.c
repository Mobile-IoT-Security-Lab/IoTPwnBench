/* Lab cipher, corrected variant of CWE-327: AES-256-CBC with a random IV and keys from a file.
 * SPDX-License-Identifier: MIT
 */
#include <stdio.h>
#include <string.h>
#include <openssl/crypto.h>
#include <openssl/evp.h>
#include <openssl/rand.h>

#define MAX_PLAIN 4096
#define KEY_LEN 32
#define MAC_KEY_LEN 32
#define IV_LEN 16
#define TAG_LEN 32
#define MAX_FRAME (IV_LEN + MAX_PLAIN + IV_LEN + TAG_LEN)
#define PREFIX "AES256-CBC:"
#define PREFIX_LEN (sizeof(PREFIX) - 1)
#define MAX_TEXT (PREFIX_LEN + MAX_FRAME * 2)

/* The keys are read from a root-provisioned file and are not part of the program.
 * The file holds the 32-byte cipher key followed by the 32-byte MAC key. */
#define KEY_FILE "/etc/iotbench/weak-cipher.key"
static unsigned char cipher_key[KEY_LEN];
static unsigned char mac_key[MAC_KEY_LEN];

static int load_keys(void)
{
    unsigned char both[KEY_LEN + MAC_KEY_LEN];
    FILE *file = fopen(KEY_FILE, "rb");
    size_t count;
    if (!file)
        return 0;
    count = fread(both, 1, sizeof(both), file);
    fclose(file);
    if (count != sizeof(both))
        return 0;
    memcpy(cipher_key, both, KEY_LEN);
    memcpy(mac_key, both + KEY_LEN, MAC_KEY_LEN);
    OPENSSL_cleanse(both, sizeof(both));
    return 1;
}

static int mac(const unsigned char *data,
               size_t length, unsigned char *tag)
{
    size_t written = 0;
    return EVP_Q_mac(NULL, "HMAC", NULL, "SHA256", NULL, mac_key, MAC_KEY_LEN,
                     data, length, tag, TAG_LEN, &written) != NULL &&
           written == TAG_LEN;
}

static int encrypt_data(const unsigned char *input,
                        size_t length)
{
    unsigned char frame[MAX_FRAME];
    EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new();
    int first = 0, last = 0, ok = 0;
    size_t frame_length;
    if (!ctx)
        goto done;
    if (RAND_bytes(frame, IV_LEN) != 1)
        goto done;
    if (EVP_EncryptInit_ex(ctx, EVP_aes_256_cbc(), NULL, cipher_key, frame) != 1 ||
        EVP_EncryptUpdate(ctx, frame + IV_LEN, &first, input, (int)length) != 1 ||
        EVP_EncryptFinal_ex(ctx, frame + IV_LEN + first, &last) != 1)
        goto done;
    frame_length = IV_LEN + (size_t)first + (size_t)last;
    if (!mac(frame, frame_length, frame + frame_length))
        goto done;
    frame_length += TAG_LEN;
    fputs(PREFIX, stdout);
    for (size_t i = 0; i < frame_length; ++i)
        printf("%02x", frame[i]);
    putchar('\n');
    ok = !ferror(stdout);
done:
    EVP_CIPHER_CTX_free(ctx);
    return ok;
}

static int hex_digit(unsigned char c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

static int decrypt_data(const unsigned char *input,
                        size_t length)
{
    unsigned char frame[MAX_FRAME], plain[MAX_PLAIN + IV_LEN], tag[TAG_LEN];
    EVP_CIPHER_CTX *ctx = NULL;
    size_t frame_length, cipher_length;
    int first = 0, last = 0, ok = 0;
    /* Accept the single newline emitted by the CLI. */
    if (length && input[length - 1] == '\n') --length;
    if (length < PREFIX_LEN || memcmp(input, PREFIX, PREFIX_LEN) != 0)
        return 0;
    length -= PREFIX_LEN;
    input += PREFIX_LEN;
    if (length % 2 || length > MAX_FRAME * 2)
        return 0;
    frame_length = length / 2;
    if (frame_length < IV_LEN + IV_LEN + TAG_LEN)
        return 0;
    cipher_length = frame_length - IV_LEN - TAG_LEN;
    if (cipher_length % IV_LEN)
        return 0;
    for (size_t i = 0; i < frame_length; ++i) {
        int high = hex_digit(input[i * 2]), low = hex_digit(input[i * 2 + 1]);
        if (high < 0 || low < 0)
            return 0;
        frame[i] = (unsigned char)((high << 4) | low);
    }
    /* Encrypt-then-MAC, the tag covers the IV and the ciphertext. */
    if (!mac(frame, frame_length - TAG_LEN, tag) ||
        CRYPTO_memcmp(tag, frame + frame_length - TAG_LEN, TAG_LEN) != 0)
        return 0;
    ctx = EVP_CIPHER_CTX_new();
    if (!ctx || EVP_DecryptInit_ex(ctx, EVP_aes_256_cbc(), NULL, cipher_key, frame) != 1 ||
        EVP_DecryptUpdate(ctx, plain, &first, frame + IV_LEN, (int)cipher_length) != 1 ||
        EVP_DecryptFinal_ex(ctx, plain + first, &last) != 1 ||
        first + last > MAX_PLAIN)
        goto done;
    ok = fwrite(plain, 1, (size_t)(first + last), stdout) == (size_t)(first + last);
done:
    OPENSSL_cleanse(plain, sizeof(plain));
    EVP_CIPHER_CTX_free(ctx);
    return ok;
}

int main(int argc, char **argv)
{
    unsigned char input[MAX_TEXT + 2];
    size_t length, limit;
    int encrypting, ok;
    if (argc != 2 ||
        (strcmp(argv[1], "encrypt") && strcmp(argv[1], "decrypt"))) {
        fputs("Usage: iotbench-weak-cipher encrypt|decrypt < input\n", stderr);
        return 1;
    }
    if (!load_keys()) {
        fputs("Cipher keys are not provisioned\n", stderr);
        return 1;
    }
    encrypting = strcmp(argv[1], "encrypt") == 0;
    limit = encrypting ? MAX_PLAIN : MAX_TEXT + 1;
    length = fread(input, 1, limit + 1, stdin);
    if (length > limit || ferror(stdin)) {
        fputs("Input exceeds the operation limit or could not be read\n", stderr);
        return 1;
    }
    ok = encrypting ? encrypt_data(input, length) : decrypt_data(input, length);
    if (!ok)
        fputs(encrypting ? "Encryption failed\n" : "Invalid encrypted frame\n", stderr);
    return ok ? 0 : 1;
}
