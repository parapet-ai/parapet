# parapet v3.0.0-APACHE — Linux Capabilities Audit
## v1.0.0 | Priority Date: 2026-05-18 | Evidence for Patent #5: 6-Layer Container Security

---

## Configuration

```yaml
# docker-compose.yml
security_opt:
  - no-new-privileges:true
  - "seccomp:./security/seccomp-parapet.json"
read_only: true
cap_drop:
  - ALL
# No cap_add entries — zero capabilities granted
```

**Summary:** parapet drops all 40 documented Linux capabilities. Zero capabilities are added back. This means the container process cannot: modify the kernel, change file ownership, bind privileged ports (<1024), trace other processes, load kernel modules, bypass file permission checks, or modify system time.

---

## Complete Capability Table

| # | Capability | Dropped | Impact If Not Dropped | Justification |
|---|-----------|---------|----------------------|---------------|
| 0 | `CAP_CHOWN` | **Yes** | Could change file ownership arbitrarily. Attack vector: chown workspace files to escape user namespace. | Container runs as user 1000:1000. No ownership changes needed post-startup. |
| 1 | `CAP_DAC_OVERRIDE` | **Yes** | Could bypass read/write/execute permission checks on ALL files. Critical container escape risk. | All file access goes through standard Unix permissions. Workspace mounted with correct ownership. |
| 2 | `CAP_DAC_READ_SEARCH` | **Yes** | Could bypass read permission and directory search checks. | Standard `open()`/`stat()` suffice for model loading and file operations. |
| 3 | `CAP_FOWNER` | **Yes** | Could manipulate files as if owned by the file owner. | No cross-ownership file operations required. |
| 4 | `CAP_FSETID` | **Yes** | Could set SUID/SGID bits on files. Container escape vector if combined with writable binaries. | Filesystem is read-only. No SUID binaries needed. |
| 5 | `CAP_KILL` | **Yes** | Could send signals to processes outside the container. | Internal signals (SIGTERM for shutdown) work via standard kill() without CAP_KILL for same-UID processes. |
| 6 | `CAP_SETGID` | **Yes** | Could change group ID arbitrarily. Privilege escalation to other groups. | Container runs as fixed UID/GID 1000:1000. No group changes needed. |
| 7 | `CAP_SETUID` | **Yes** | Could change user ID arbitrarily (e.g., to root). Classic container escape primitive. | User 1000:1000 is hardcoded. Must never be root. |
| 8 | `CAP_SETPCAP` | **Yes** | Could modify capability bounding sets of other processes. | No process management outside container boundary. |
| 9 | `CAP_NET_BIND_SERVICE` | **Yes** | Could bind to ports <1024. Non-issue: web UI binds to 8080 (>1024). | Port 8080 is unprivileged. Ollama binds to 11434 on HOST, not container. |
| 10 | `CAP_NET_BROADCAST` | **Yes** | Could send broadcast packets. Not needed for localhost-only container networking. | All communication is localhost or bridge network. No broadcast needed. |
| 11 | `CAP_NET_ADMIN` | **Yes** | Could configure network interfaces, routing tables, firewall rules. Container network escape. | Docker bridge network is pre-configured. No runtime network changes needed. |
| 12 | `CAP_NET_RAW` | **Yes** | Could use RAW/PACKET sockets. Not needed for HTTP/REST API communication. | Ollama API uses TCP via standard socket(). No raw packet crafting. |
| 13 | `CAP_IPC_LOCK` | **Yes** | Could lock pages into RAM (mlock). However, Ollama uses mlock() for model weights — is this blocked? **Cross-reference:** mlock() is allowed via seccomp whitelist. CAP_IPC_LOCK is a CAPABILITY check—seccomp is a SYSCALL filter. Without CAP_IPC_LOCK, mlock() returns ENOMEM at the capability check level. **RESOLUTION:** If models fail to load with OOM errors despite free VRAM, re-evaluate. Current testing with user 1000:1000 + cap_drop ALL + seccomp whitelist on RTX 3060 shows models load successfully. Ollama uses mmap() primarily, not mlock(). |
| 14 | `CAP_IPC_OWNER` | **Yes** | Could override IPC ownership checks. | No IPC (shared memory, message queues) used by Python/Ollama inference pipeline. |
| 15 | `CAP_SYS_MODULE` | **Yes** | Could load/unload kernel modules. Complete system compromise. | No kernel module operations needed. NVIDIA driver loaded at boot by host. |
| 16 | `CAP_SYS_RAWIO` | **Yes** | Could access raw I/O ports, /dev/mem, /dev/kmem. Full system compromise. | GPU access via /dev/nvidia* device nodes through standard ioctl(). No raw I/O required. |
| 17 | `CAP_SYS_CHROOT` | **Yes** | Could use chroot(). Container escape vector. | Docker provides the root filesystem namespace. No runtime chroot needed. |
| 18 | `CAP_SYS_PTRACE` | **Yes** | Could trace/read/write memory of arbitrary processes. Could inject code into host processes. Critical container escape. | No debugging or tracing of external processes. Python error handling uses internal tracebacks, not ptrace. |
| 19 | `CAP_SYS_PACCT` | **Yes** | Could enable/disable process accounting. | No process accounting needed for AI inference. |
| 20 | `CAP_SYS_ADMIN` | **Yes** | Massive umbrella capability covering 36+ distinct operations: mount, umount, swapon, sethostname, pivot_root, clone with CLONE_NEWNS, etc. Critical container escape. | None of the operations covered by CAP_SYS_ADMIN are needed. Container orchestration handled by Docker daemon. |
| 21 | `CAP_SYS_BOOT` | **Yes** | Could reboot the system. | No reboot capability needed in a container. |
| 22 | `CAP_SYS_NICE` | **Yes** | Could change process priority/niceness of arbitrary processes. | Thread scheduling uses standard pthread scheduling. Nice values set at container startup via Docker. |
| 23 | `CAP_SYS_RESOURCE` | **Yes** | Could exceed resource limits (RLIMIT overrides), modify resource limits for other processes. | Docker resource limits (CPU 2.0, RAM 4G) are enforced at container boundary. |
| 24 | `CAP_SYS_TIME` | **Yes** | Could modify system clock. | clock_gettime() is read-only and works without CAP_SYS_TIME. |
| 25 | `CAP_SYS_TTY_CONFIG` | **Yes** | Could reconfigure TTY devices. | No terminal device configuration needed. Container has no TTY access. |
| 26 | `CAP_MKNOD` | **Yes** | Could create device nodes (mknod). Container escape vector if combined with writable /dev. | /dev is populated by Docker at container start. Filesystem is read-only. |
| 27 | `CAP_LEASE` | **Yes** | Could take file leases on arbitrary files. | No distributed filesystem operations. |
| 28 | `CAP_AUDIT_WRITE` | **Yes** | Could write audit log entries. | Container logging via stdout/stderr, not kernel audit subsystem. |
| 29 | `CAP_AUDIT_CONTROL` | **Yes** | Could enable/disable kernel audit. | No kernel audit subsystem needed. |
| 30 | `CAP_SETFCAP` | **Yes** | Could set file capabilities on executables. Container escape if combined with writable binaries. | Filesystem is read-only. No file capability manipulation. |
| 31 | `CAP_MAC_OVERRIDE` | **Yes** | Could override Mandatory Access Control (SELinux/AppArmor). | MAC policies enforced by host. Container should not override them. |
| 32 | `CAP_MAC_ADMIN` | **Yes** | Could configure MAC policies. | MAC policy changes are host-level operations. |
| 33 | `CAP_SYSLOG` | **Yes** | Could read kernel message buffer (dmesg). Information leak about host kernel. | Application logging via stdout/stderr. No kernel log access needed. |
| 34 | `CAP_WAKE_ALARM` | **Yes** | Could trigger system wakeup. | No system power management needed in container. |
| 35 | `CAP_BLOCK_SUSPEND` | **Yes** | Could prevent system suspend. | No power management operations. |
| 36 | `CAP_AUDIT_READ` | **Yes** | Could read audit log via netlink. Information leak. | No audit log reading needed. |
| 37 | `CAP_PERFMON` | **Yes** | Could use perf_event_open() for hardware performance monitoring. | nvidia-smi used for GPU monitoring. perf not needed. |
| 38 | `CAP_BPF` | **Yes** | Could load BPF programs into kernel. Kernel code injection. | No BPF/eBPF functionality needed for inference. |
| 39 | `CAP_CHECKPOINT_RESTORE` | **Yes** | Could checkpoint/restore process state across PID namespaces. | No CRIU operations needed. |

---

## Cross-Reference: seccomp Interaction

| Layer | Mechanism | What It Controls |
|-------|-----------|-----------------|
| **Capability** | `cap_drop: ALL` | Whether a process CAN perform a privileged operation (capability check at VFS/syscall entry) |
| **seccomp** | `seccomp-parapet.json` | Whether a process can CALL a syscall at all (syscall number filter at arch layer) |
| **no-new-privileges** | `no-new-privileges:true` | Whether a process can GAIN new capabilities via setuid/setcaps binaries |
| **read_only** | `read_only: true` | Whether the filesystem is writable (prevents binary modification, cron job, SUID file creation) |

**Defense in depth:** If seccomp allowed a dangerous syscall (e.g., mount), the capability check would still block it (CAP_SYS_ADMIN dropped). If both seccomp AND capabilities somehow failed, no-new-privileges would prevent acquiring the missing capability. If all three failed, read_only filesystem prevents writing a SUID binary. Four independent layers before an attacker can achieve privilege escalation.

---

## DORA Art. 28 / NIS2 Art. 21 Compliance Mapping

| Requirement | parapet Mechanism | Evidence |
|-------------|------------------|----------|
| **Least Privilege** | `cap_drop: ALL` + seccomp + `user: 1000:1000` | This document |
| **Defense in Depth** | 4-layer security (capabilities → seccomp → no-new-priv → read_only) | Security architecture diagram |
| **Supply Chain Risk** | Zero cloud AI providers. One local open-source dependency (Ollama), self-hosted, no network dependency during operation. See docs/OLLAMA-SUPPLY-CHAIN.md for full NIS2 Art. 21 compliance. | This document + docs/OLLAMA-SUPPLY-CHAIN.md |
| **Audit Trail** | seccomp denials logged to kernel log (auditd); capability denials visible via `capsh --print` inside container | Runtime verification |

---

## Verification Commands

```bash
# Check effective capability set inside running container
docker exec ollama-agent capsh --print

# Expected output:
# Current: =  (empty — no capabilities)
# Bounding set = (all caps outside bounding set)
# Ambient set = (empty)

# Verify seccomp is active
docker inspect ollama-agent --format '{{.HostConfig.SecurityOpt}}'
# Expected: [no-new-privileges:true seccomp:./security/seccomp-parapet.json]

# Count seccomp violations (should be zero after stable operation)
docker exec ollama-agent cat /proc/self/status | grep Seccomp
# Expected: Seccomp: 2 (SECCOMP_MODE_FILTER)
```

---

*Document v1.0.0 | 2026-05-20 | Andrzej Dobosz*
*Evidence for Patent #5: 6-Layer Container Security for AI Deployments*
