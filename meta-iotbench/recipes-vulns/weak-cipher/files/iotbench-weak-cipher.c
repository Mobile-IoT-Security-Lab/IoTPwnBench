/* Intentionally vulnerable lab cipher: obsolete 3DES with hardcoded keys and IV.
 * SPDX-License-Identifier: MIT
 */
#include <stdio.h>
#include <string.h>
#include <openssl/crypto.h>
#include <openssl/evp.h>

#define MAX_PLAIN 4096
#define KEY_LEN 24
#define MAC_KEY_LEN 32
#define IV_LEN 8
#define TAG_LEN 32
#define MAX_FRAME (IV_LEN + MAX_PLAIN + IV_LEN + TAG_LEN)
#define PREFIX "3DES-CBC:"
#define PREFIX_LEN (sizeof(PREFIX) - 1)
#define MAX_TEXT (PREFIX_LEN + MAX_FRAME * 2)

/* Public benchmark constants embedded in every device image. */
static const unsigned char hardcoded_key[KEY_LEN] = {
    0x01, 0x23, 0x45, 0x67, 0x89, 0xab, 0xcd, 0xef,
    0x23, 0x45, 0x67, 0x89, 0xab, 0xcd, 0xef, 0x01,
    0x45, 0x67, 0x89, 0xab, 0xcd, 0xef, 0x01, 0x23
};
static const unsigned char hardcoded_iv[IV_LEN] = {
    0x12, 0x34, 0x56, 0x78, 0x90, 0xab, 0xcd, 0xef
};
static const unsigned char hardcoded_mac_key[MAC_KEY_LEN] = {
    0xa0, 0xa1, 0xa2, 0xa3, 0xa4, 0xa5, 0xa6, 0xa7,
    0xa8, 0xa9, 0xaa, 0xab, 0xac, 0xad, 0xae, 0xaf,
    0xb0, 0xb1, 0xb2, 0xb3, 0xb4, 0xb5, 0xb6, 0xb7,
    0xb8, 0xb9, 0xba, 0xbb, 0xbc, 0xbd, 0xbe, 0xbf
};

static int mac(const unsigned char *data,
               size_t length, unsigned char *tag)
{
    size_t written = 0;
    return EVP_Q_mac(NULL, "HMAC", NULL, "SHA256", NULL, hardcoded_mac_key, MAC_KEY_LEN,
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
    memcpy(frame, hardcoded_iv, IV_LEN);
    /* CWE-327: three-key Triple DES with a 64-bit block size. */
    if (EVP_EncryptInit_ex(ctx, EVP_des_ede3_cbc(), NULL, hardcoded_key, hardcoded_iv) != 1 ||
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
    /* The public MAC key makes this check forgeable; it only detects corruption. */
    if (CRYPTO_memcmp(frame, hardcoded_iv, IV_LEN) != 0 ||
        !mac(frame, frame_length - TAG_LEN, tag) ||
        CRYPTO_memcmp(tag, frame + frame_length - TAG_LEN, TAG_LEN) != 0)
        return 0;
    ctx = EVP_CIPHER_CTX_new();
    if (!ctx || EVP_DecryptInit_ex(ctx, EVP_des_ede3_cbc(), NULL, hardcoded_key, hardcoded_iv) != 1 ||
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
