---
name: iac-review
description: Infrastructure-as-code review procedure. Trigger when a Terraform, CloudFormation, Kubernetes, or Helm change is proposed.
---

# IaC review

## Procedure

1. **Read the plan, not only the diff.** `terraform plan` / `kubectl diff` /
   `helm diff` shows create/update/destroy. A one-line diff can destroy a
   database.
2. **Classify each resource.** Create, update in place, replace, destroy.
   Replace/destroy on a stateful resource is a `BLOCKER` until a migration is
   named.
3. **Trace exposure.** Public IP, public bucket, `0.0.0.0/0`, public LB, public
   database, public Kubernetes service. Is it intentional?
4. **Trace identity.** IAM role/policy, service account, trust policy,
   wildcard action/resource. Least privilege with conditions.
5. **Check encryption and secrets.** At rest, in transit, in state, in env, in
   ConfigMap. Secret manager vs plaintext.
6. **Check resilience.** Multi-AZ, backups/PITR, health checks, resource limits,
   PodDisruptionBudget, autoscaling.
7. **Check state.** Remote backend, locking, encryption, access control. State
   contains secrets; who can read it?
8. **Check policy.** Org guardrails, tagging, retention, deletion protection,
   cost.

## Terraform prompts

```bash
terraform plan -out=tfplan
terraform show -json tfplan | jq '.resource_changes[] | select(.change.actions != ["no-op"])'
```

## Kubernetes prompts

```bash
kubectl diff -f .
kubectl get pod -o yaml | rg "securityContext|resources|hostPath|privileged"
```

## Verdict

```
RESOURCE | action | exposure | identity | encryption | rollback
```

`BLOCKER` for a destructive replacement with no migration; `CRITICAL` for public
data or wildcard IAM; `HIGH` for missing encryption/backups. If there is no
plan, say which findings are provisional.
