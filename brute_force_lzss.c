#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>

uint8_t target[] = {0x5A, 0x07, 0x2A, 0x00, 0x68, 0x00};

int get_nibble(uint8_t* rom, int rom_size, int* ptr, int* nibble_state, uint8_t* curr_byte) {
    (*nibble_state)++;
    if ((*nibble_state) & 1) {
        if (*ptr >= rom_size) return -1;
        *curr_byte = rom[(*ptr)++];
        return *curr_byte >> 4;
    } else {
        return *curr_byte & 0x0F;
    }
}

int get_byte(uint8_t* rom, int rom_size, int* ptr, int* nibble_state, uint8_t* curr_byte) {
    int hi = get_nibble(rom, rom_size, ptr, nibble_state, curr_byte);
    if (hi == -1) return -1;
    int lo = get_nibble(rom, rom_size, ptr, nibble_state, curr_byte);
    if (lo == -1) return -1;
    return (hi << 4) | lo;
}

int decompress(uint8_t* rom, int rom_size, int start_addr, uint8_t* out, int max_len) {
    int ptr = start_addr;
    int nibble_state = 0;
    uint8_t curr_byte = 0;
    
    uint8_t history[4] = {0xFF, 0xFF, 0xFF, 0xFF};
    int dd = 0;
    int out_len = 0;
    
    int flag_byte = get_byte(rom, rom_size, &ptr, &nibble_state, &curr_byte);
    if (flag_byte == -1) return out_len;
    int flag_bits = 8;
    
    while (out_len < max_len) {
        int cmd = get_nibble(rom, rom_size, &ptr, &nibble_state, &curr_byte);
        if (cmd == -1) return out_len;
        
        if (cmd <= 6) {
            int val = (cmd << 3);
            int nxt = get_nibble(rom, rom_size, &ptr, &nibble_state, &curr_byte);
            if (nxt == -1) return out_len;
            val = val | nxt;
            
            if (flag_bits == 0) {
                flag_byte = get_byte(rom, rom_size, &ptr, &nibble_state, &curr_byte);
                if (flag_byte == -1) return out_len;
                flag_bits = 8;
            }
            int bit = (flag_byte >> 7) & 1;
            flag_byte = (flag_byte << 1) & 0xFF;
            flag_bits--;
            
            val = val | (bit << 7);
            
            out[out_len++] = val;
            history[dd] = val;
            dd = (dd + 1) & 3;
        } else if (cmd == 7) {
            int length = 0;
            while (1) {
                int b = get_byte(rom, rom_size, &ptr, &nibble_state, &curr_byte);
                if (b == -1) return out_len;
                length += b;
                if (b != 0xFF) break;
            }
            
            int e3_idx = (dd + 2) & 3;
            uint8_t e3 = history[e3_idx];
            
            int e5_idx = (e3_idx + 1) & 3;
            uint8_t e5 = history[e5_idx];
            
            for (int i = 0; i < length; i++) {
                if (out_len >= max_len) break;
                out[out_len++] = e3;
                if (out_len >= max_len) break;
                out[out_len++] = e5;
            }
        } else if (cmd == 8) {
            break;
        } else if (cmd == 9) {
            out[out_len++] = 0x00;
            history[dd] = 0x00;
            dd = (dd + 1) & 3;
        } else if (cmd == 0xA) {
            out[out_len++] = 0xFF;
            history[dd] = 0xFF;
            dd = (dd + 1) & 3;
        } else if (cmd >= 0xB && cmd <= 0xE) {
            uint8_t val = history[cmd - 0xB];
            out[out_len++] = val;
            history[dd] = val;
            dd = (dd + 1) & 3;
        } else {
            return out_len;
        }
    }
    return out_len;
}

int main() {
    FILE* f = fopen("Nage Libre - Seijaku no Suishin (Japan).sfc", "rb");
    if (!f) return 1;
    fseek(f, 0, SEEK_END);
    int rom_size = ftell(f);
    fseek(f, 0, SEEK_SET);
    uint8_t* rom = malloc(rom_size);
    fread(rom, 1, rom_size, f);
    fclose(f);
    
    uint8_t out[256];
    
    for (int i = 0; i < rom_size - 100; i++) {
        int len = decompress(rom, rom_size, i, out, 256);
        if (len >= 6) {
            for (int j = 0; j <= len - 6; j++) {
                if (memcmp(out + j, target, 6) == 0) {
                    printf("FOUND TARGET IN COMPRESSED STREAM AT 0x%06X\n", i);
                    return 0;
                }
            }
        }
    }
    printf("Not found.\n");
    return 0;
}
