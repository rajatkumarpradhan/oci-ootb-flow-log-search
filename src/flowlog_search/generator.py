"""Deterministic synthetic VCN flow-log record generator.

Record shape mirrors the fields OCI flow logs carry (source/destination
address and port, protocol, action, bytes, packets), so queries written here
translate to real Logging Search queries by name.
"""
import random

# A small synthetic VCN: a public web tier, an app tier, and a scanner host
# hammering SSH so the example queries have something to find.
HOSTS = {
    "web-1": "10.0.1.10",
    "web-2": "10.0.1.11",
    "app-1": "10.0.2.10",
    "db-1": "10.0.2.20",
    "scanner": "198.51.100.77",
    "client-a": "203.0.113.5",
    "client-b": "203.0.113.6",
}
PORT_NAMES = {22: "ssh", 80: "http", 443: "https", 1521: "oracle-db", 8080: "app"}


def generate(count: int = 400, seed: int = 20261030, start_epoch: int = 1793318400) -> list[dict]:
    """Return `count` synthetic flow-log records, deterministic for a given seed."""
    rng = random.Random(seed)
    records = []
    for i in range(count):
        kind = rng.choices(["web", "app-db", "scan", "egress"], weights=[45, 25, 20, 10])[0]
        if kind == "web":
            src, dst = rng.choice(["client-a", "client-b"]), rng.choice(["web-1", "web-2"])
            dport = rng.choice([80, 443])
            action = "ACCEPT" if rng.random() < 0.97 else "REJECT"
        elif kind == "app-db":
            src, dst, dport = "app-1", "db-1", 1521
            action = "ACCEPT"
        elif kind == "scan":
            src = "scanner"
            dst = rng.choice(["web-1", "web-2", "app-1", "db-1"])
            dport = rng.choice([22, 22, 22, 3389])
            # NSGs reject almost everything the scanner tries
            action = "REJECT" if rng.random() < 0.95 else "ACCEPT"
        else:
            src, dst, dport = "app-1", "client-a", 443
            action = "ACCEPT"
        records.append({
            "time": start_epoch + i * 60 + rng.randint(0, 30),
            "src_ip": HOSTS[src],
            "src_host": src,
            "src_port": rng.randint(1024, 65000),
            "dst_ip": HOSTS[dst],
            "dst_host": dst,
            "dst_port": dport,
            "dst_port_name": PORT_NAMES.get(dport, str(dport)),
            "protocol": "6",
            "action": action,
            "bytes": rng.randint(60, 90000) if action == "ACCEPT" else rng.randint(40, 200),
            "packets": rng.randint(1, 120),
        })
    return records
