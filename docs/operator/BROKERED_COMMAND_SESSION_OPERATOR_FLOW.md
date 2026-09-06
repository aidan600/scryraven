# Brokered Command Session Operator Flow

Status: current operator guidance for the credentialed local-command doorman.

## Purpose

The doorman is operator infrastructure for one human-approved local command.
It privately reads the selected environment file, starts one shell-free child
with the exact target argv, captures stdout and stderr, redacts configured
secret values, and writes sanitized output outside the repository.

The doorman owns environment-file custody, process plumbing, timeout handling,
and output redaction. It does not choose providers or models, decide search or
answer policy, interpret evidence, or become part of the product runtime.
Product and test code must not import it.

## When to use it

Normal local work that does not need private environment values can run
directly.

Use the doorman when a human has approved a credentialed command and its
complete argv. The target command remains responsible for its own behavior.
The doorman does not add retries, routing, budgets, or application policy.

## Standard invocation

From the repository root, prepare output paths outside the repository:

    $stdout = 'C:\tmp\broker.stdout.txt'
    $stderr = 'C:\tmp\broker.stderr.txt'
    $status = 'C:\tmp\broker.status.json'

Run one command with the repository-local private environment:

    .\.venv\Scripts\python.exe scripts\run_brokered_command_once.py --repo-root C:\Users\aidan\ScryRaven --repo-env --stdout $stdout --stderr $stderr --status $status --replace-output --timeout-seconds 90 --target-current-python -- <exact-target> <exact-argv> <tokens>

Everything after the required separator is the exact target argv. The
separator prevents option ambiguity and the child is launched with shell=False.
Use --env-file followed by a privately supplied path instead of --repo-env only
when that is the approved environment source.

Output files must be absolute, must have existing parents, and must be outside
the repository. Existing output requires explicit --replace-output authority.
The optional status file contains only sanitized lifecycle fields and safe
failure codes.

## Custody sequence

1. The public parent validates paths and argv but never opens or parses the
   environment file.
2. The private child receives a one-session nonce and the private file path.
3. The private child parses the file, builds the target environment, and removes
   its own session variables before launch.
4. The target receives the constructed environment, exact argv, and repository
   working directory.
5. Captured output is normalized and exact secret values from secret-shaped
   environment names are replaced before sanitized files are written.
6. The private child clears in-memory environment mappings before exit.

The parent does not receive raw target output. A timeout terminates the target
process tree and records a structural timeout status. A target launch failure
records a safe launch-failure status without exposing an operating-system error.

## Review boundary

The doorman is a credential-custody boundary, not a general sandbox and not an
authorization system. Exact command approval remains with the human operator.
Keep private environment files, keys, raw provider responses, prompts, logs,
and generated private material out of controller output and source control.
