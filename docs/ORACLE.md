# Hosting the Mieux API on Oracle Cloud (Always Free)
1. Create an account at cloud.oracle.com (home region: Paris or Frankfurt). A card is asked only to verify identity; Always Free resources are not billed.
2. Compute > Instances > Create instance: image Ubuntu 22.04, shape VM.Standard.A1.Flex (Ampere) with 2 OCPU and 12 GB RAM (or VM.Standard.E2.1.Micro), boot volume 100 GB, assign a public IP, and download the SSH key.
3. Networking > the instance's subnet > Security list > add ingress rules for TCP 80 and 443 from 0.0.0.0/0.
4. `ssh -i key.pem ubuntu@<ip>` then `curl -fsSL https://raw.githubusercontent.com/Helmus101/mieux/main/deploy/oracle/setup.sh -o setup.sh && bash setup.sh`
5. From your Mac, from the backend folder: `scp -i key.pem off_local.db op_local.db ubuntu@<ip>:/srv/mieux/data/` and `scp -i key.pem foodiq.db ubuntu@<ip>:/srv/mieux/data/mieux.db`
6. On the VM: `cd /srv/mieux && sudo docker compose restart api`, then open `https://<ip-with-dashes>.sslip.io/v1/health`.
