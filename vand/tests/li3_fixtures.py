encoding = "ascii"

FAKE_LI3_BINARY_DATA = [
    "1309,327,327,328,327".encode(encoding),
    "&,1,114,006880".encode(encoding),
    ",32,39,0,79,000000".encode(encoding),
]
TEST_LI3_CONFIG = {
    "li3": {
        "1": {
            "dev_name": "Li3-Test-1",
            "mac_address": "FF:69:4E:38:44:B3",
            "service_uuid": "FOO",
            "characteristic": "BAR",
            "timeout": 0.1,
        },
        "2": {
            "dev_name": "Li3-Test-2",
            "mac_address": "FF:69:4E:35:CE:71",
            "service_uuid": "FOO",
            "characteristic": "BAR",
            "timeout": 0.1,
        },
    }
}
