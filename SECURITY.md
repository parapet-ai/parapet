# Security Policy / Polityka bezpieczenstwa

## Supported Versions / Wspierane wersje

| Version | Supported |
|---------|-----------|
| 1.x (main) | ✅ Active development |

## Reporting a Vulnerability / Zglaszanie podatnosci

**EN:** Do not open a public issue. Email `awdobosz@proton.me` with details. Response within 48 hours.

**PL:** Nie otwieraj publicznego zgloszenia. Wyslij szczegoly na `awdobosz@proton.me`. Odpowiedz w ciagu 48 godzin.

## Security Model / Model bezpieczenstwa

Parapet AI implements five independent security layers:

1. **VM Isolation** — NAT mode, agent cannot reach physical LAN
2. **iptables** — `PARAPET-EGRESS` chain filters all outbound traffic
3. **DNS Sinkhole** — CoreDNS restricts resolution to authorized endpoints only
4. **Container Hardening** — read-only rootfs, cap_drop ALL, no-new-privileges, seccomp
5. **Secret Isolation** — credentials mounted as `/run/secrets/`, never in environment variables

See `security/` directory for detailed hardening documentation.
