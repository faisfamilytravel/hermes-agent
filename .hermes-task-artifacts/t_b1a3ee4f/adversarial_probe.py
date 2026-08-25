from hermes_cli.execution_provenance import _redacted_execution_path

cases = [
    (["hermes", "chat", "--API_KEY", "alpha"], ["alpha"], True),
    (["hermes", "chat", "--access-token=beta"], ["beta"], True),
    (["hermes", "chat", "--private_key", "gamma"], ["gamma"], True),
    (["hermes", "chat", "--auth-token", "delta", "--client-secret=epsilon"], ["delta", "epsilon"], True),
    (["hermes", "chat", "--authorization", "Bearer zeta"], ["Bearer zeta"], True),
    (["hermes", "chat", "--query=eta=theta"], ["eta=theta"], True),
    (["hermes", "chat", "--prompt", "iota"], ["iota"], True),
    (["hermes", "chat", "--token-count", "4096"], [], False),
    (["hermes", "chat", "--password-policy", "strict"], [], False),
    (["hermes", "chat", "--secret-santa", "enabled"], [], False),
    (["hermes", "chat", "--monkey", "visible"], [], False),
    (["hermes", "chat", "--my-key", "identifier"], [], False),
]

for index, (argv, forbidden, expect_redaction) in enumerate(cases, start=1):
    rendered = _redacted_execution_path(argv)
    assert all(value not in rendered for value in forbidden), (index, rendered)
    assert ("[REDACTED]" in rendered) is expect_redaction, (index, rendered)
    print(f"probe {index:02d}: PASS: {rendered}")

print(f"ADVERSARIAL_PROBES_PASS={len(cases)}")
