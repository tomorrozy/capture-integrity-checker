# Security Policy

CaptureIntegrityChecker is a defensive security baseline. We take reports
seriously and appreciate good-faith research that makes the detection layer more
robust or reveals bugs in the module itself.

## Supported versions

| Version | Supported |
|---|---|
| v0.1.x (in development) | ✅ |
| older / unreleased forks | ❌ |

## Reporting a vulnerability

**Please do not open a public issue for a security-sensitive report.**

Use GitHub private vulnerability reporting: go to the repository's **Security →
Advisories → "Report a vulnerability"** button. This opens a private draft
advisory visible only to you and the maintainers. (Maintainers: enable this under
Settings → Advanced Security → Private vulnerability reporting.)

If that channel is unavailable, contact the maintainers privately via the contact
listed on the repository profile before any public disclosure.

Please include:
- Affected version / commit and platform (Linux distro + kernel, or Windows build).
- Camera model / virtual-camera implementation and how it was configured.
- Step-by-step reproduction and, if possible, a minimal proof of concept.
- Observed vs. expected `integrity_score` / `evidence`, and the security impact.
- Whether the issue is a code bug, a detection bypass, or a false positive.

We aim to acknowledge reports within **7 days** and to agree on a coordinated
disclosure timeline before any public write-up. Best-effort, not a guarantee.

## What counts as a vulnerability

In scope:
- Code-level bugs in the module (crashes, unsafe parsing, injection, dependency
  issues) that affect integrators.
- **Novel detection bypasses** that defeat the default configuration within the
  documented scope (e.g. a virtual camera that scores as trustworthy without the
  attacker having to modify kernel modules or inject artificial timing).
- False-positive regressions that misclassify common physical cameras.

## Known limitations (not vulnerabilities)

These are documented boundaries (see README and `docs/threat-model.md`), not
security bugs. Reports that push these boundaries are welcome as research or
enhancement issues, but are triaged accordingly:
- Hardware-level HDMI / capture-card injection (out of scope for v0.1).
- macOS / CoreMediaIO cameras (not covered in v0.1).
- A recompiled `v4l2loopback` kernel module that erases the `driver` string.
- A virtual camera that injects artificial reconfiguration delay to mimic physical
  negotiation. This is an arms race; the module raises cost, it does not end it.

The project deliberately makes **no claim** of being a complete fix or of
lab-grade APCER. Bypasses that require the attacker to already control the kernel
or driver stack are expected, not surprises.

## Safe harbor

We support good-faith security research conducted against your own devices and
installations. Do not test against systems you do not own or have authorization
to assess, do not weaponize proofs of concept against third parties, and do not
exfiltrate or store real users' frame content. Reports that follow these rules
will be treated as authorized research.