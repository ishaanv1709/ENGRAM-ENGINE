# Free hosting independent of the laptop

Status: the current public website remains a temporary tunnel to the laptop. An always-on deployment has not been provisioned because no cloud account/server access has been supplied.

The selected free-only candidate is Oracle Cloud Always Free. Oracle's current compute guide lists an Ampere A1 allowance equivalent to **2 OCPUs and 12 GB RAM**, with 200 GB total eligible block/boot storage in the home region. Check the actual Console limits and Always Free cost estimate before creation. Do not select larger trial-only resources or upgrade to paid services for this deployment. [Current Oracle limits](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm).

Free capacity may be unavailable and Oracle can reclaim idle eligible instances. This can keep the app independent of the laptop, but it cannot establish guaranteed permanent uptime. Oracle's signup documentation may require card verification; those details belong on Oracle's site, not in this chat. [Oracle signup information](https://docs.oracle.com/en-us/iaas/Content/GSG/Tasks/signingup_topic-Sign_Up_for_Free_Oracle_Cloud_Promotion.htm).

## What to provide

1. Create your Oracle Free Tier account and an Always Free-eligible Ubuntu 24.04 ARM server within the current allowance. A 100 GB boot disk leaves room for the model, image and application data while remaining within a new account's 200 GB total allowance.
2. Add the contents of `data/collective/deploy/id_ed25519.pub` to the server's authorized SSH keys during creation. The dedicated private key remains on this laptop in the ignored data directory. Do not paste it into chat.
3. Provide the server's public IP address, SSH username (normally `ubuntu`) and its SSH host-key fingerprint from a trusted console if available. No Oracle account password is needed if this SSH route is used.
4. For a stable free hostname, create a DuckDNS subdomain and point it at the server's public IP. Provide the hostname. No DuckDNS token is needed when you set the record yourself. The current temporary tunnel address cannot be transferred as a permanent hostname.
5. Permit the intended web ports in OCI networking and allow SSH only from the deployment client's address. This will be checked before cutover rather than opening database ports publicly.

No paid resources are authorized. Provider inference will use visitors' own keys; the deployment does not need to copy the operator's Groq/search keys into a shared guest configuration.

## Deployment work after access is available

- Check the CPU architecture and published images. The pinned FalkorDB v4.16.0 manifest was inspected and includes ARM64 and AMD64. PostgreSQL, Qdrant, the Python environment and CPU embedding runtime still require validation on the actual server.
- Install a native Linux Docker runtime and application dependencies. Rebuild/download sandbox wheels for ARM instead of uploading the laptop's x86-only wheel directory.
- Run the API, long-lived workers and real CPU embedding service as managed services with automatic restart. Persist PostgreSQL, FalkorDB, Qdrant, artifact files, Mem0 history and the provider-encryption secret.
- Configure an HTTPS reverse proxy and the exact production origin. Keep database, embedding and Docker administration endpoints private. Preserve sandbox restrictions on the new host.
- Handle data migration explicitly. Existing artifact records contain Windows filesystem paths and cannot simply be restored unchanged on Linux. Verify hashes after rebasing artifact paths. Move the encryption secret with encrypted connection data. A new domain also needs a deliberate workspace/session handoff if existing visitor workspaces are to remain accessible there.
- Verify reboot recovery, browser flows, independent sandbox workspaces, data retention and provider-key isolation before replacing the demo link. Live model/provider validation remains a separate, credential-backed check.

This is a preparation record, not a claim that an unprovisioned cloud server was deployed or tested.

## Beginner walkthrough in the Oracle Console

1. Open <https://www.oracle.com/cloud/free/> and create the account. Select your home region deliberately; Always Free compute must be created there. Complete Oracle's identity/card checks on its own site. Keep the account on the free plan.
2. Sign in at <https://cloud.oracle.com/>. Open the navigation menu, choose **Compute**, then **Instances**. Verify the selected region is your home region.
3. Choose **Create instance**. Use the name `engram-collective`. Your root compartment is sufficient for a first deployment.
4. In **Image and shape**, choose an Always Free eligible **Ubuntu 24.04** ARM image. The prepared installer currently targets Ubuntu 24.04, not Oracle Linux.
5. Change the shape to **VM.Standard.A1.Flex**. Allocate **2 OCPUs** and **12 GB memory** for one server, assuming no other instances consume your allowance. Do not choose an A2/A4 shape, GPU instance or paid image.
6. For placement, leave a compatible availability domain selected. If creation reports out of host capacity, try another availability domain in the same region or retry later. Do not switch to a paid shape to bypass the shortage.
7. Under networking, create or select a VCN with an internet gateway and a **public subnet**. Assign a **public IPv4 address** to the primary network interface. Keep the API and databases behind the server rather than exposing database ports.
8. Under **Add SSH keys**, choose **Upload public key files**. Upload `D:\Neurohacks\data\collective\deploy\id_ed25519.pub`. This file is public. The similarly named file without `.pub` is the private key and stays on this computer.
9. If the Console offers a text box instead, paste the single line from the `.pub` file. Do not generate a different key unless you intend to configure a separate access route.
10. Set the boot volume to **100 GB**, at the free eligible/default performance tier. Account-wide boot and block volume allocations must remain within the current 200 GB allowance. Avoid adding paid backup or performance options.
11. Review the image, shape and free eligibility. Trial credits are not proof that a resource remains free after the trial ends. Create only the eligible resource described here.
12. Choose **Create**. Wait until its lifecycle state becomes **Running**, then open the instance details.
13. Copy the **public IP address** and **username** from the instance access section. For Ubuntu the username is normally `ubuntu`.
14. In the primary VNIC's subnet/security rules, allow TCP **22** only from your current public client IP with `/32`. Before the final website check, TCP **80** and **443** must be reachable publicly for HTTPS. Do not add public rules for 5432/55432, 6379/56379, 6333/56333, 8091 or Docker administration.
15. Send only the public IP and username to this chat. If available, also provide the server's SSH host-key fingerprint from Oracle's console connection so first connection can be verified.
16. Once the server is reachable, I can install the application and configure HTTPS. A stable hostname will also be required: create a free DuckDNS name, point its address at the server's public IP, and provide the resulting hostname. No DuckDNS password or token needs to be shared if you set the record yourself.

Oracle's resource policy: <https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm>. Console creation reference: <https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/launchinginstance.htm>.

## Prepared installation assets

- `infra/linux/install.sh`: an Ubuntu 24.04 installer for `/opt/engram`, including native-architecture sandbox wheels, the locked application dependencies, production frontend, Docker databases, three systemd services and Caddy HTTPS.
- `infra/linux/compose.yml`: separately named persistent production stores; all published database ports bind only to loopback.
- `scripts/production-environment.py`: exclusively creates a fresh environment with random database passwords, secure cookies, one HTTPS origin and no operator provider credentials. Existing environments are never overwritten.
- The dedicated public deployment key is already available at the path above. Source code and the actual 1.34 GB GGUF model must be transferred before installation. The script does not pretend to migrate existing Windows artifact paths or browser identities.

Local preparation checks passed: Bash syntax validation, Docker Compose configuration validation and parsing of a separately generated BYOK-only environment. Remote image builds, systemd startup, HTTPS, reboot persistence, sandboxing and data migration are still untested until a real server is supplied. A valid installation script is not evidence of a deployed server.
