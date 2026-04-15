Created two files in `ec2_autoscaling/`:

- **`main.tf`** — Launch template, ASG with rolling instance refresh, CPU-based scaling policies, IAM role with least-privilege SSM access, encrypted EBS, IMDSv2 enforced, restrictive security groups.
- **`user_data.sh`** — Templatefile-driven bootstrap that pulls secrets from SSM Parameter Store (not hardcoded), configures the app, verifies backend connectivity with retry logic, sets up CloudWatch agent, and starts the service under a dedicated non-root user.

Key security choices: no credentials in user_data (uses IAM role + SSM), IMDSv2 required (hop limit 1), encrypted volumes, egress-restricted security group.