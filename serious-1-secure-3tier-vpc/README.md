# Serious 1 — Secure 3-Tier VPC

## What we are building, and why

A secure three-tier network in AWS, built in the AWS Management
Console first, then rebuilt later in Terraform as Serious 3.

Three tiers means three separate layers, each in its own subnets,
with traffic only allowed to flow one way, from the outside in:

- **Web tier (public):** faces the internet. It holds the load
  balancer and the web servers. Only this tier gets a route to the
  internet gateway.
- **App tier (private):** the application servers. They can be
  reached only from the web tier. They have no direct internet
  access, and no public IP addresses.
- **DB tier (private):** the database, RDS MySQL. It can be reached
  only from the app tier, on port 3306 only. It never talks to the
  internet, and it never gets a public IP address.

That separation is the whole point. If the web tier is exposed,
the database is still not reachable from the internet. A recruiter
or interviewer can check this in one look at the route tables and
security groups, which is why this is a serious project and not a
single-script demo.

No Terraform is used for this build. Terraform comes later, in
Serious 3, when we rebuild this exact VPC in code.

## Design decisions

- **Region: us-east-1 (N. Virginia).** Confirmed from the VPC
  dashboard screenshot on 2026-11-09. This replaces the older
  us-east-2 plan, because the console, CloudShell, and the AI
  projects are already in us-east-1.
- **VPC: p1-vpc, CIDR 10.0.0.0/16.** A /16 gives 65,536 addresses,
  enough to split into six /24 subnets with room left over.
  10.0.0.0/16 is private RFC 1918 space, so it does not clash with
  the public internet.
- **Availability Zones: 2, us-east-1a and us-east-1b.** Every tier
  gets one subnet in each AZ. If one AZ fails, the other AZ still
  has a web, app, and DB subnet. That is high availability at the
  network level, before we add a load balancer or Auto Scaling.
- **Subnets, all /24:**
  - Web: 10.0.0.0/24 (us-east-1a), 10.0.1.0/24 (us-east-1b)
  - App: 10.0.10.0/24 (us-east-1a), 10.0.11.0/24 (us-east-1b)
  - DB: 10.0.20.0/24 (us-east-1a), 10.0.21.0/24 (us-east-1b)
- **DNS hostnames and DNS resolution: on.** Without them, EC2
  instances and RDS do not get usable DNS names inside the VPC,
  and the load balancer and database connections break in ways
  that are hard to debug.
- **Database: RDS MySQL,** in the DB tier only, in a later step.
- **Cost rule:** VPC, subnets, route tables, and security groups
  cost $0 by themselves. NAT Gateway, Application Load Balancer,
  and RDS charge hourly while they exist. Those are built later,
  verified, and deleted after the demo unless Haileab explicitly
  says to keep them up.

## Build order

- Step 1 — Verify what already exists in us-east-1, before
  creating anything (this step)
- Step 2 — Create p1-vpc, if it does not already exist
- Step 3 — Create the six subnets
- Step 4 — Create the route tables, public / private / DB
- Step 5 — Create and attach the internet gateway, public route
  only
- Step 6 — Security groups, chained ALB -> app -> DB
- Step 7 — Network ACLs, one per tier
- Step 8 — NAT Gateway, build-verify-delete in one session
- Step 9 — Application Load Balancer and Auto Scaling
- Step 10 — RDS MySQL in the DB tier, then end-to-end test,
  screenshots, cleanup, and GitHub push

Each step is added to this file with its explanation as we do it,
in the same words used in chat, so this file is the GitHub
documentation, not a separate summary written afterwards.

---

## Step 1 — Verify what already exists, before creating anything

### What we are doing

We are opening the VPC dashboard, Your VPCs, and Subnets in
us-east-1, and reading what is already there, before we click
Create VPC.

### Why we do this first

A VPC is not free to duplicate. If a p1-vpc already exists and we
create a second one with the same CIDR, we get two networks with
the same addresses, overlapping subnets, and a confusing mess to
clean up. The dashboard on 2026-11-09 showed 1 VPC, 6 subnets,
1 internet gateway, and 0 NAT gateways. That count matches the
Week 1 plan, but a count is not proof.

There is a specific trap here: every AWS account starts with a
default VPC in each region. In us-east-1 the default VPC also
has 1 VPC, 6 subnets, 1 internet gateway, and 1 route table.
So the 1 VPC / 6 subnets we saw could be the default VPC, not
p1-vpc. The only way to tell is to open Your VPCs and read the
name and CIDR.

We also check route tables here, because the plan needs 3 route
tables: public, private, and DB. The dashboard showed only 1
route table. That is what the default VPC has, and it is also
what a half-finished p1-vpc would have. Either way, we do not
proceed to security groups or NAT until this is resolved.

### How to do it

1. In the AWS Console, region United States (N. Virginia),
   us-east-1, open VPC > VPC dashboard.
2. Click **Your VPCs** in the left menu.
   - Record: VPC name, VPC ID, IPv4 CIDR, state, DNS hostnames,
     DNS resolution, and whether it is the default VPC.
   - Pass if it is named p1-vpc, CIDR 10.0.0.0/16, state
     Available, DNS hostnames on, DNS resolution on.
   - Fail, and go to Step 2, if it is the default VPC, usually
     CIDR 172.31.0.0/16, or any other CIDR, or if no p1-vpc
     is listed.
3. Click **Subnets** in the left menu.
   - Record for each of the 6 subnets: name, subnet ID, VPC,
     IPv4 CIDR, Availability Zone, and whether it auto-assigns
     a public IPv4 address.
   - Pass if the names and CIDRs match the design above, in
     us-east-1a and us-east-1b, with auto-assign public IPv4
     on the web subnets only.
   - Fail if the subnets belong to the default VPC, use
     172.31.x.x CIDRs, or are spread across six AZs instead
     of two.
4. Click **Route Tables** and **Internet Gateways**.
   - Record how many route tables exist, their names, and
     which subnets are associated with each. Record whether
     the internet gateway is attached, and to which VPC.
   - At this stage, 1 route table is expected if only the
     default VPC exists, or if p1-vpc was created without its
     custom route tables yet. 3 route tables is the Week 1
     pass state.

### What we found in the dashboard screenshot, 2026-11-09

- Region: us-east-1
- VPCs: 1
- Subnets: 6
- Route Tables: 1
- Internet Gateways: 1
- Network ACLs: 1
- Security Groups: 7
- NAT Gateways: 0

Screenshot: `screenshots/vpc-subnets/vpc-dashboard-us-east-1.png`

This is Step 1 evidence only. It does not verify the VPC name,
CIDR, subnet names, or route tables. Those are verified in the
Your VPCs and Subnets clicks above.

### Cost of this step

$0. Reading the console creates nothing.

### Step 1 result — 2026-11-09, re-confirmed 2026-11-10 after restart

**Fail, as expected if this was the default VPC.**

Haileab reported: the only VPC listed is the default VPC,
CIDR **172.31.0.0/16**. That is not p1-vpc, and it is not
10.0.0.0/16. The 6 subnets and 1 internet gateway on the
dashboard belonged to that default VPC.

Restart screenshot, 2026-11-10, Your VPCs details page:
VPC ID vpc-0a0cff632591d850c, State Available, Default VPC Yes,
IPv4 CIDR 172.31.0.0/16, DNS resolution Enabled, DNS hostnames
Enabled, Tenancy default, Main route table
rtb-01768e52b8a28c2c6, Main network ACL acl-0cb13827f3b6182be.
Screenshot: `screenshots/vpc-subnets/your-vpcs-default-vpc.png`

Haileab reported: the only VPC listed is the default VPC,
CIDR **172.31.0.0/16**. That is not p1-vpc, and it is not
10.0.0.0/16. The 6 subnets and 1 internet gateway on the
dashboard belonged to that default VPC.

Do NOT delete the default VPC, and do NOT build the three tiers
inside it. The default VPC is a flat, public network. Its
subnets are all public by default, which is the opposite of the
private app and DB tiers we need. We leave it alone and create
a new, separate VPC for this project.

---

## Step 2 — Create p1-vpc, 10.0.0.0/16

### What we are doing

We are creating a new, empty VPC named p1-vpc, with IPv4 CIDR
10.0.0.0/16, in us-east-1, with DNS hostnames and DNS
resolution turned on. Nothing else yet. No subnets, no route
tables, no internet gateway in this step.

### Why we do it this way

A VPC is the isolated network boundary for everything that
follows. Subnets, route tables, security groups, the load
balancer, and RDS all live inside this VPC, and they cannot
talk to resources outside it unless we explicitly give them a
route. That isolation is why we create our own VPC instead of
using the default one.

10.0.0.0/16 is private RFC 1918 space. The /16 means the first
two numbers, 10.0, are fixed for this VPC, and the last two
numbers are free for subnets inside it. That gives us 65,536
addresses, and each /24 subnet we carve out of it gets 256
addresses. That is why the subnet plan, 10.0.0.0/24,
10.0.1.0/24, 10.0.10.0/24, 10.0.11.0/24, 10.0.20.0/24,
10.0.21.0/24, fits cleanly inside 10.0.0.0/16, with no overlap
and no clash with the default VPC's 172.31.0.0/16.

DNS hostnames and DNS resolution must be on. DNS resolution
lets resources inside the VPC resolve AWS service names and
each other's private DNS names. DNS hostnames gives EC2
instances a public DNS name when they have a public IP, and
RDS a DNS endpoint. If either is off, the load balancer,
Auto Scaling, and RDS steps later fail in confusing ways,
with instances that launch but cannot be reached by name.
Turning them on now, at VPC creation, avoids that.

We choose **VPC only**, not **VPC and more**. "VPC and more"
is AWS's wizard that creates subnets, route tables, and a NAT
gateway for you in one go. That hides the exact CIDRs, AZs,
and route tables we need to be able to explain in an
interview, and it can create a NAT gateway that starts
charging hourly before we are ready for it. Creating the VPC
alone, then adding each piece ourselves in the next steps,
is slower, but it is the point of this project: you can say
exactly what is in the network, and why.

### How to do it

1. In the AWS Console, region us-east-1, open VPC > Your VPCs.
2. Click **Create VPC**.
3. Under **Resources to create**, choose **VPC only**.
4. **Name tag:** `p1-vpc`
5. **IPv4 CIDR block:** choose **IPv4 CIDR manual input**,
   enter `10.0.0.0/16`
6. **IPv6 CIDR block:** No IPv6 CIDR block
7. **Tenancy:** Default
8. **DNS hostnames:** Enable
9. **DNS resolution:** Enable
10. Click **Create VPC**.

### How to verify it

Back on Your VPCs, you should now see 2 VPCs in us-east-1:
the default VPC, 172.31.0.0/16, and the new one.

For p1-vpc, check:
- Name: p1-vpc
- IPv4 CIDR: 10.0.0.0/16
- State: Available
- DNS hostnames: Enabled
- DNS resolution: Enabled
- Default VPC: No

Take a screenshot of the Your VPCs page showing both VPCs,
and save it as `screenshots/vpc-subnets/your-vpcs-p1-vpc.png`.

### Cost of this step

$0. A VPC by itself, with no NAT gateway, load balancer, or
RDS, does not charge.

### Step 2 result — 2026-11-10, 14:23 CST

**Created, but one setting is wrong. Do not move to Step 3 yet.**

Screenshot: `screenshots/vpc-subnets/your-vpcs-p1-vpc-created.png`

- VPC ID: vpc-08694d42074a60709
- Name: p1-vpc
- IPv4 CIDR: 10.0.0.0/16 — correct
- State: Available — correct
- Default VPC: No — correct
- DNS resolution: Enabled — correct
- **DNS hostnames: Disabled — wrong, must be Enabled**
- Subnets: 0 — correct for this step, subnets come next
- Route tables: 1 — correct for this step, that is the main
  route table created with the VPC

The DNS hostnames setting was supposed to be Enabled at
creation. It shows Disabled, so it was either left off in the
form, or the console did not apply it. Either way, we fix it
before subnets, because EC2 and RDS later need DNS hostnames
to get usable names inside the VPC.

Fix, still inside Step 2:
1. On Your VPCs, select p1-vpc.
2. Click **Actions > Edit DNS hostnames**.
3. Check **Enable DNS hostnames**, then Save.
4. Re-open the p1-vpc details page and check that DNS
   hostnames now says Enabled, with DNS resolution still
   Enabled.

Fix confirmed 2026-11-10, Haileab report: "enabled".
DNS hostnames is now Enabled, DNS resolution is still
Enabled. Step 2 is now complete: p1-vpc, 10.0.0.0/16,
Available, Default VPC No, DNS hostnames Enabled, DNS
resolution Enabled, Subnets 0, Route tables 1.

---

## Step 3 — Create the six subnets

### What we are doing

We are carving p1-vpc into six subnets, two per tier, one in
each Availability Zone. A subnet is a smaller network inside
the VPC, tied to one AZ. Resources in a subnet live in that
AZ, and they inherit that subnet's public/private character
from its route table and its auto-assign public IP setting.

### Why six, and why these CIDRs

Two AZs per tier is the minimum for high availability. If
us-east-1a fails, us-east-1b still has a web, an app, and a DB
subnet, so the application can keep running in the other AZ.
One subnet per tier would be a single point of failure.

Each subnet is a /24, which is 256 addresses. AWS reserves
5 of those in every subnet, so 251 are usable for instances
and RDS. That is more than enough for this project, and it
keeps the address plan easy to read: the third number tells
you the tier, 0-1 for web, 10-11 for app, 20-21 for DB, and
the AZ is the last bit, 0 for a, 1 for b.

| Name | AZ | CIDR | Auto-assign public IPv4 |
| --- | --- | --- | --- |
| p1-web-a | us-east-1a | 10.0.0.0/24 | Yes |
| p1-web-b | us-east-1b | 10.0.1.0/24 | Yes |
| p1-app-a | us-east-1a | 10.0.10.0/24 | No |
| p1-app-b | us-east-1b | 10.0.11.0/24 | No |
| p1-db-a | us-east-1a | 10.0.20.0/24 | No |
| p1-db-b | us-east-1b | 10.0.21.0/24 | No |

Auto-assign public IPv4 is on for the web subnets only.
That means an EC2 instance launched in a web subnet gets a
public IP by default, so it can be reached from the internet
through the load balancer. App and DB subnets are No, so
instances and RDS there get private IPs only, by default.
That setting alone does not make a subnet private, the route
table in the next step does that, but it is the first layer:
a DB instance should never get a public IP by accident.

Never choose "No preference" for the Availability Zone. If
AWS picks the AZ for you, you can end up with both web
subnets in the same AZ, or app and DB in different AZs from
their pair, and the high-availability design breaks silently.
Pick 1a or 1b explicitly for every subnet.

Make sure you select p1-vpc, not the default VPC, for every
subnet. The default VPC already has 6 subnets in 1a-1f, with
172.31.x.x CIDRs. Those are not these subnets. If you create
a subnet in the wrong VPC, delete it and start that subnet
again in p1-vpc.

### How to do it

1. In the AWS Console, region us-east-1, open VPC > Subnets.
2. Click **Create subnet**.
3. **VPC ID:** select `p1-vpc`.
4. Add the first subnet as a row:
   - **Subnet name:** `p1-web-a`
   - **Availability Zone:** `us-east-1a`
   - **IPv4 CIDR block:** `10.0.0.0/24`
5. Click **Add new subnet** and add the next row, repeating
   the name, AZ, and CIDR from the table above, until all
   six rows are filled in. Check each row before you click
   Create: name, AZ, and CIDR must match the table exactly.
6. Click **Create subnet**.
7. After creation, open each subnet and set auto-assign
   public IPv4:
   - For p1-web-a and p1-web-b: **Actions > Modify auto-assign
     IP settings > Enable auto-assign public IPv4 address**,
     then Save.
   - For p1-app-a, p1-app-b, p1-db-a, and p1-db-b: leave
     auto-assign public IPv4 off. If the console shows it
     on for any of them, turn it off the same way.

If the console only lets you create one subnet at a time in
your view, create them one by one with the same values above.
The result is the same, six subnets in p1-vpc.

Form trap, seen 2026-11-10: the Create subnet form defaults
to Availability Zone "No preference" and IPv4 subnet CIDR
"10.0.0.0/20". Do NOT create with those defaults. Change AZ
to us-east-1a or 1b explicitly, and change the CIDR to the
/24 from the table, for example 10.0.0.0/24 for p1-web-a.
Screenshot: `screenshots/vpc-subnets/create-subnet-form.png`

### How to verify it

On VPC > Subnets, filter by VPC `p1-vpc`. You should see
exactly 6 subnets, all State Available, with the names,
CIDRs, and AZs from the table above, and no other subnets
in p1-vpc.

Take a screenshot of the Subnets page filtered to p1-vpc,
and save it as `screenshots/vpc-subnets/subnets-p1-vpc.png`.

### Cost of this step

$0. Subnets do not charge.

### Result, in progress

First subnet created 2026-11-10: **p1-web-a**,
`subnet-0e9bfcfe786d239d3`, Available, p1-vpc,
10.0.0.0/24, 251 available, us-east-1a, route table
rtb-06df2d4e647339a22 (the main route table, for now).
Internet access shows "No (private)", which is expected
before Step 5 adds the internet gateway route. One thing
still to fix on this subnet: Auto-assign public IPv4
address is No, it must be Yes for the web subnets. Fix it
with Actions > Modify auto-assign IP settings > Enable
auto-assign public IPv4 address. Do the same for
p1-web-b when it is created. The other four subnets
(app-a, app-b, db-a, db-b) stay No.

All six created 2026-11-10, names verified in screenshot:
p1-web-a `subnet-0e9bfcfe786d239d3`, p1-web-b
`subnet-0712e577148484352`, p1-app-a
`subnet-08d3f235c56d5045c`, p1-app-b
`subnet-0bdc5860e5903e93f`, p1-db-a
`subnet-00c50c095c8401b69`, p1-db-b
`subnet-0f730dea656980038`, all Available, all in p1-vpc.
The p1-app-a subnet was first created as "p1-app-1" and
then renamed to p1-app-a. The five subnets after p1-web-a
were then deleted and recreated with auto-assign public
IPv4 enabled, and then edited so auto-assign is Yes only
on the two web subnets, p1-web-a and p1-web-b, No on
app/db, per Haileab's report 2026-11-10. Current subnet
IDs, from the 14:57 screenshot: p1-web-a
`subnet-0e9bfcfe786d239d3`, p1-web-b
`subnet-0ca5116b6192f24a8`, p1-app-a
`subnet-02f9674b607c52d07`, p1-app-b
`subnet-04440b9211f8322f7`, p1-db-a
`subnet-01b906d224767a59a`, p1-db-b
`subnet-0f730dea656980038`. CIDRs and AZs verified
2026-11-10 from Haileab's full paste, all six match the
table exactly, auto-assign Yes only on the two web
subnets, No on app/db, all Available, 251 addresses each,
route table rtb-06df2d4e647339a22 (the main route table,
for now), network ACL acl-02ad964f67e93bb07, Internet
"No (private)", expected before Step 5. Step 3 is
complete.

---

## Step 4 — Create the route tables, public / private / DB

### What we are doing

We are creating three route tables, one per tier, and
associating each tier's two subnets with its table. A
route table is the set of rules that tells traffic in a
subnet where to go next. A subnet uses exactly one route
table, and that table is what makes the subnet public or
private, not just its name or its auto-assign setting.

### Why three, and why not use the main route table

Right now all six subnets are associated with p1-vpc's
main route table, rtb-06df2d4e647339a22. That table has
only one route, the local route for 10.0.0.0/16, so
traffic can move inside the VPC but nowhere else. If we
left all six subnets on that one table, we could not
give the web tier an internet route without also giving
it to the app and DB tiers, and the whole point of the
three tiers is that only the web tier gets an internet
route.

So we create three separate tables:

| Route table | Subnets associated | Routes now | Routes later |
| --- | --- | --- | --- |
| p1-rt-public | p1-web-a, p1-web-b | local 10.0.0.0/16 only | + 0.0.0.0/0 to the internet gateway, in Step 5 |
| p1-rt-private | p1-app-a, p1-app-b | local 10.0.0.0/16 only | + 0.0.0.0/0 to the NAT gateway, in Step 8, for outbound-only internet access |
| p1-rt-db | p1-db-a, p1-db-b | local 10.0.0.0/16 only | never gets an internet route, local only forever |

The DB table never gets a 0.0.0.0/0 route. That is the
design: RDS in the DB tier can be reached from the app
tier on port 3306, and it can reach nothing on the
internet, and nothing on the internet can reach it.

Do not edit the main route table, and do not associate
any p1 subnet with it after this step. It stays as the
VPC's default, unused by our six subnets. Also make
sure you create these tables in p1-vpc, not in the
default VPC.

### How to do it

Create the three tables first:

1. In the AWS Console, region us-east-1, open VPC >
   Route tables.
2. Click **Create route table**.
3. **Name:** `p1-rt-public`
   **VPC:** select `p1-vpc`
4. Click **Create route table**.
5. Repeat for `p1-rt-private` in p1-vpc, and then for
   `p1-rt-db` in p1-vpc.

Then associate the subnets, one table at a time:

6. Select `p1-rt-public`, open the **Subnet associations**
   tab, click **Edit subnet associations**, check
   `p1-web-a` and `p1-web-b`, then **Save associations**.
7. Select `p1-rt-private`, Subnet associations > Edit
   subnet associations, check `p1-app-a` and `p1-app-b`,
   then Save associations.
8. Select `p1-rt-db`, Subnet associations > Edit subnet
   associations, check `p1-db-a` and `p1-db-b`, then Save
   associations.

Do not add any routes in this step. Each new table
already has the local 10.0.0.0/16 route, and that is all
it should have for now. The internet gateway route goes
in Step 5, in the public table only.

### How to verify it

On VPC > Route tables, filter by VPC `p1-vpc`. You
should see 4 route tables: the main table
rtb-06df2d4e647339a22 with 0 explicit subnet
associations, plus p1-rt-public, p1-rt-private, and
p1-rt-db, each with 2 explicit associations.

Check each table's Routes tab: each should show only
`10.0.0.0/16 | local | Active`, no 0.0.0.0/0 route yet.

Take a screenshot of the Route tables page filtered to
p1-vpc, and save it as
`screenshots/vpc-subnets/route-tables-p1-vpc.png`.

### Cost of this step

$0. Route tables do not charge.

### Result, in progress — fix needed

Checked 2026-11-10, 15:11-15:12 CST, two screenshots:

- **p1-rt-public, rtb-08d24a8878b8af29a — correct.**
  Explicit associations (2): p1-web-b
  subnet-0ca5116b6192f24a8 10.0.1.0/24, p1-web-a
  subnet-0e9bfcfe786d239d3 10.0.0.0/24. Screenshot:
  `screenshots/vpc-subnets/step4-route-tables-p1-rt-public-2-web-subnets.png`

- **p1-rt-private, rtb-0fc6acae21be36950 — wrong.**
  Explicit associations (4): p1-db-b
  subnet-0f730dea656980038 10.0.21.0/24, p1-db-a
  subnet-01b906d224767a59a 10.0.20.0/24, p1-app-a
  subnet-02f9674b607c52d07 10.0.10.0/24, p1-app-b
  subnet-04440b9211f8322f7 10.0.11.0/24. It must have
  only the 2 app subnets. Screenshot:
  `screenshots/vpc-subnets/step4-route-tables-p1-rt-private-4-subnets-app-and-db.png`

- **p1-rt-db — not shown, still to create.** No p1-rt-db
  appears in these screenshots.

Fix, still inside Step 4:
1. Create p1-rt-db in p1-vpc.
2. Associate p1-db-a and p1-db-b with p1-rt-db. That
   moves them out of p1-rt-private.
3. Re-check p1-rt-private: it should then show 2
   subnets, p1-app-a and p1-app-b only.
4. Re-check the Route tables page filtered to p1-vpc:
   4 tables total (main + public + private + db), each
   custom table with 2 explicit associations, each with
   only the local 10.0.0.0/16 route for now.

Fix confirmed 2026-11-10, 15:19 CST, screenshot:
**p1-rt-db, rtb-0cdc9fa65334e18a8 — correct.**
Explicit associations (2): p1-db-b
subnet-0f730dea656980038 10.0.21.0/24, p1-db-a
subnet-01b906d224767a59a 10.0.20.0/24. Subnets without
explicit associations (0). Screenshot:
`screenshots/vpc-subnets/step4-route-tables-p1-rt-db-2-db-subnets.png`
(E12 in the evidence log.)

A subnet can be associated with only one route table,
so moving the DB subnets to p1-rt-db removes them from
p1-rt-private, which should now show 2 subnets, app-a
and app-b only. Step 4 is now complete: p1-rt-public
2 web, p1-rt-private 2 app, p1-rt-db 2 db, each local
10.0.0.0/16 only for now.

---

## Step 5 — Create and attach the internet gateway, public route only

### What we are doing

We are creating an internet gateway, p1-igw, attaching
it to p1-vpc, and adding one route, 0.0.0.0/0 to that
gateway, in p1-rt-public only. An internet gateway is
the VPC-level door to the internet. It does nothing on
its own — a subnet can only use it if its route table
has a route pointing to it.

### Why only in the public table

This is the step that actually makes the web tier
public and keeps the other two tiers private. The web
subnets already have auto-assign public IPv4 set to
Yes, so an instance there gets a public IP. With the
0.0.0.0/0 route in p1-rt-public, traffic from the
internet can reach that public IP, and traffic from the
web tier can go out to the internet.

The app and DB tables get no 0.0.0.0/0 route in this
step. Do not add the route to p1-rt-private or
p1-rt-db, and do not add it to the main route table.
If you did, the app or DB tier would become directly
reachable from the internet, and the three-tier design
would be broken. The app tier will get outbound-only
internet access later, through a NAT gateway in Step 8.
The DB tier never gets an internet route.

Note the trap: the default VPC already has its own
internet gateway, igw-01644b6331e6fef1b. That one
belongs to the default VPC. Do not attach it to p1-vpc,
and do not use it here. Create a new one for p1-vpc.

### How to do it

Create and attach the gateway first:

1. In the AWS Console, region us-east-1, open VPC >
   Internet gateways.
2. Click **Create internet gateway**.
3. **Name tag:** `p1-igw`
4. Click **Create internet gateway**.
5. Select the new `p1-igw`, click **Actions > Attach to
   VPC**, select `p1-vpc`, then **Attach internet
   gateway**.

Then add the route, in the public table only:

6. Open VPC > Route tables, select `p1-rt-public`.
7. Open the **Routes** tab, click **Edit routes**.
8. Click **Add route**:
   - **Destination:** `0.0.0.0/0`
   - **Target:** Internet Gateway, then select `p1-igw`
9. Click **Save changes**.

Do not add a route in p1-rt-private, p1-rt-db, or the
main route table in this step.

### How to verify it

- On VPC > Internet gateways, p1-igw should show
  State Available and Attached VPC p1-vpc.
- On VPC > Route tables, p1-rt-public, Routes tab,
  should show two routes:
  - `10.0.0.0/16 | local | Active`
  - `0.0.0.0/0 | igw-xxxx | Active`
  where igw-xxxx is the ID of p1-igw.
- p1-rt-private and p1-rt-db, Routes tab, should still
  show only `10.0.0.0/16 | local | Active`, no
  0.0.0.0/0 route.
- On VPC > Subnets, p1-web-a and p1-web-b should now
  show Internet access "Yes (public)", while the app
  and DB subnets still show "No (private)".

Take a screenshot of the p1-rt-public Routes tab, and
save it as
`screenshots/vpc-subnets/step5-route-table-p1-rt-public-igw-route.png`.

### Cost of this step

$0. An internet gateway does not charge by the hour.
Data transfer charges would only apply later, when
traffic actually flows through it.

### Result

Verified 2026-11-10, 15:24 CST, screenshot:
p1-rt-public, rtb-08d24a8878b8af29a, Routes (2):
- `0.0.0.0/0 | igw-0c83de58a50570... | Active`
- `10.0.0.0/16 | local | Active`

That IGW ID is different from the default VPC's
igw-01644b6331e6fef1b, so it is the new p1-igw, not the
default one. The same screenshot also confirms the
Step 4 fix: p1-rt-private rtb-0fc6acae21be36950 now
shows 2 subnets, and p1-rt-db rtb-0cdc9fa65334e18a8
shows 2 subnets. Screenshot:
`screenshots/vpc-subnets/step5-route-table-p1-rt-public-igw-route.png`
(E13 in the evidence log.)

Step 5 is complete. The IGW name / attachment page
was not shown in this screenshot, so that part is
recorded from the route target ID above, not from a
separate IGW details screenshot.

---

## Step 6 — Security groups, chained ALB → app → DB

### What we are doing

We are creating three security groups, one per tier,
with inbound rules that chain them together: the
internet can only reach the load balancer, the load
balancer can only reach the app tier, and the app tier
can only reach the database. A security group is a
stateful virtual firewall attached to an instance, a
load balancer, or RDS. Unlike a route table, which
decides where traffic goes, a security group decides
which traffic is allowed in at all.

### Why chained by group, not by IP

If we allowed the app tier from 0.0.0.0/0, anyone on
the internet could reach the app servers directly,
bypassing the load balancer. If we allowed the DB from
a subnet CIDR like 10.0.10.0/24, any instance in that
subnet could reach the DB, even one that should not.
By using the previous tier's security group as the
source, only resources that actually carry that group
can connect, even if their IP changes. That is the
chain: ALB → app → DB.

| Security group | Attached to (later) | Inbound rule |
| --- | --- | --- |
| p1-sg-alb | Application Load Balancer | HTTP, TCP 80, from 0.0.0.0/0 |
| p1-sg-app | App EC2 instances | HTTP, TCP 80, from p1-sg-alb only |
| p1-sg-db | RDS MySQL | MySQL/Aurora, TCP 3306, from p1-sg-app only |

Outbound rules: leave the default outbound rule,
All traffic to 0.0.0.0/0, for now. That lets the app
servers reach out through the NAT gateway in Step 8
for updates, and it keeps this step focused on the
inbound chain, which is the security control that
matters here. Tightening outbound rules is a later
hardening step, not part of Step 6.

Create them in this order, ALB first, then app, then
DB, because each one needs the previous group's ID as
its inbound source.

### How to do it

1. In the AWS Console, region us-east-1, open EC2 >
   Security Groups, or VPC > Security Groups.
2. Click **Create security group**.
3. **Security group name:** `p1-sg-alb`
   **Description:** `Load balancer, internet-facing, HTTP from anywhere`
   **VPC:** select `p1-vpc`
   **Inbound rules:** Add rule, Type HTTP, Protocol TCP,
   Port range 80, Source Type Custom, Source
   `0.0.0.0/0`
4. Click **Create security group**.
5. Create `p1-sg-app` the same way:
   **Description:** `App servers, HTTP only from the load balancer`
   **VPC:** `p1-vpc`
   **Inbound rules:** Type HTTP, Protocol TCP, Port
   range 80, Source Type Custom, Source `p1-sg-alb`
   (pick the security group from the list, do not type
   an IP address).
6. Create `p1-sg-db` the same way:
   **Description:** `RDS MySQL, only from the app tier`
   **VPC:** `p1-vpc`
   **Inbound rules:** Type MySQL/Aurora, Protocol TCP,
   Port range 3306, Source Type Custom, Source
   `p1-sg-app`.

Make sure all three are created in p1-vpc, not in the
default VPC. The default VPC already has 7 security
groups — those are not these three.

### How to verify it

On EC2 > Security Groups, filter by VPC `p1-vpc`.
You should see 3 new security groups, plus the
default security group that came with p1-vpc.

Check each group's Inbound rules tab:
- p1-sg-alb: HTTP 80 from 0.0.0.0/0, and nothing else.
- p1-sg-app: HTTP 80 from p1-sg-alb, and nothing else.
- p1-sg-db: MySQL/Aurora 3306 from p1-sg-app, and
  nothing else.

Take a screenshot of the Security Groups list filtered
to p1-vpc, and save it as
`screenshots/security-groups/security-groups-p1-vpc.png`.
Save a screenshot of each group's Inbound rules tab as
well, if you want the evidence pack to show the chain
in full.

### Cost of this step

$0. Security groups do not charge.

### Result, in progress

Created 2026-11-10, 15:37 CST, screenshot:
- **p1-sg-alb, sg-00e39906c1d91de7e**, p1-vpc,
  "Load balancer, int..."
- **p1-sg-app, sg-0dc782d147f0112b**, p1-vpc,
  "App Servers, HTTP..."
- **p1-sg-db, sg-063e10e3231772a8b**, p1-vpc,
  "RDS MySQL, only..."
  Banner: "Security group (sg-063e10e3231772a8b |
  p1-sg-db) was created successfully"

All three are in p1-vpc, with the right names and
descriptions. Screenshot:
`screenshots/security-groups/step6-security-groups-p1-vpc-list.png`
(E14 in the evidence log.)

Inbound rules verified 2026-11-10, 15:39 CST, from
Haileab's pasted Inbound rules (1 rule per group, E15
in the evidence log, no screenshot file for this paste):
- p1-sg-alb: sgr-0069e2f383ab9152e, IPv4, HTTP, TCP 80,
  from 0.0.0.0/0.
- p1-sg-app: sgr-083179c562c66f69d, HTTP, TCP 80, from
  sg-00e39906c1d91de7e / p1-sg-alb.
- p1-sg-db: sgr-06d76cd466a3a5844, MYSQL/Aurora, TCP
  3306, from sg-0dc782d147f0112b / p1-sg-app.

Step 6 is complete. The chain is exactly as designed:
internet → ALB on 80 → app on 80 from ALB only →
DB on 3306 from app only.

---

## Step 7 — Network ACLs, one per tier

### What we are doing

We are creating three network ACLs, one per tier, and
associating each tier's two subnets with its NACL. A
network ACL is a stateless, subnet-level firewall. It
is the second layer of defence, behind the security
groups: security groups are precise and stateful, they
remember a connection and automatically allow the
return traffic; NACLs are coarse and stateless, they
check every packet in both directions, so return
traffic needs its own explicit rule.

That is why every NACL below has an ephemeral-ports
rule, 1024-65535. When a server replies, or when it
makes an outbound request, the reply comes back on a
high, ephemeral port. Without that rule, a stateless
NACL would block the reply even though the security
group allowed the request.

### Why three, and what each allows

NACLs are coarse on purpose. They use CIDRs, not
security groups, so they allow traffic from the whole
VPC CIDR where the security group allows it only from
one group. The security group is the precise control;
the NACL is the broad backup that stops a whole tier
being reached from the wrong place.

| Network ACL | Subnets | Inbound | Outbound |
| --- | --- | --- | --- |
| p1-nacl-web | p1-web-a, p1-web-b | 100 HTTP 80 from 0.0.0.0/0 ALLOW; 110 HTTPS 443 from 0.0.0.0/0 ALLOW; 120 ephemeral 1024-65535 from 0.0.0.0/0 ALLOW; * DENY | 100 HTTP 80 to 0.0.0.0/0 ALLOW; 110 HTTPS 443 to 0.0.0.0/0 ALLOW; 120 ephemeral 1024-65535 to 0.0.0.0/0 ALLOW; * DENY |
| p1-nacl-app | p1-app-a, p1-app-b | 100 HTTP 80 from 10.0.0.0/16 ALLOW; 110 ephemeral 1024-65535 from 10.0.0.0/16 ALLOW; * DENY | 100 MySQL 3306 to 10.0.0.0/16 ALLOW; 110 HTTPS 443 to 0.0.0.0/0 ALLOW; 120 ephemeral 1024-65535 to 10.0.0.0/16 ALLOW; * DENY |
| p1-nacl-db | p1-db-a, p1-db-b | 100 MySQL 3306 from 10.0.0.0/16 ALLOW; 110 ephemeral 1024-65535 from 10.0.0.0/16 ALLOW; * DENY | 100 ephemeral 1024-65535 to 10.0.0.0/16 ALLOW; * DENY |

The DB NACL has no 0.0.0.0/0 rule at all, inbound or
outbound. That is deliberate: the DB tier talks only
inside the VPC, on 3306 in and on ephemeral ports out.
The app NACL's outbound HTTPS 443 to 0.0.0.0/0 is for
outbound updates later, through the NAT gateway in
Step 8 — it does not allow inbound traffic from the
internet, because its inbound rules allow only
10.0.0.0/16.

Rule numbers matter: NACLs are checked in number
order, lowest first, and the first matching rule wins.
The final * rule is DENY, so anything not explicitly
allowed is blocked.

Do not edit the default NACL, acl-02ad964f67e93bb07,
which currently allows all traffic and is associated
with all six subnets. Associating a subnet with a
custom NACL moves it off the default one. The default
NACL stays as the VPC default, unused by our six
subnets after this step.

### How to do it

Create the three NACLs first:

1. In the AWS Console, region us-east-1, open VPC >
   Network ACLs.
2. Click **Create network ACL**.
3. **Name:** `p1-nacl-web`
   **VPC:** select `p1-vpc`
4. Click **Create network ACL**.
5. Repeat for `p1-nacl-app` in p1-vpc, and then for
   `p1-nacl-db` in p1-vpc.

Then, for each NACL, add its inbound and outbound
rules from the table above:

6. Select `p1-nacl-web`, open the **Inbound rules**
   tab, click **Edit inbound rules**, add rules 100,
   110 and 120 as above, then Save. Open the
   **Outbound rules** tab, click **Edit outbound
   rules**, add rules 100, 110 and 120 as above, then
   Save.
7. Repeat for `p1-nacl-app` with its inbound rules
   100 and 110, and outbound rules 100, 110 and 120.
8. Repeat for `p1-nacl-db` with its inbound rules
   100 and 110, and outbound rule 100.

Then associate the subnets, one NACL at a time:

9. Select `p1-nacl-web`, open the **Subnet
   associations** tab, click **Edit subnet
   associations**, check `p1-web-a` and `p1-web-b`,
   then Save.
10. Select `p1-nacl-app`, Subnet associations > Edit
    subnet associations, check `p1-app-a` and
    `p1-app-b`, then Save.
11. Select `p1-nacl-db`, Subnet associations > Edit
    subnet associations, check `p1-db-a` and
    `p1-db-b`, then Save.

### How to verify it

On VPC > Network ACLs, filter by VPC `p1-vpc`. You
should see 4 NACLs: the default acl-02ad964f67e93bb07
with 0 explicit subnet associations, plus
p1-nacl-web, p1-nacl-app, and p1-nacl-db, each with 2
explicit associations.

Check each NACL's Inbound and Outbound rules tabs
against the table above, and check in particular that
p1-nacl-db has no 0.0.0.0/0 rule anywhere.

Take a screenshot of the Network ACLs list filtered
to p1-vpc, and save it as
`screenshots/security-groups/network-acls-p1-vpc.png`.

### Cost of this step

$0. Network ACLs do not charge.

### Result, in progress

Associations verified 2026-11-10, 15:47-15:48 CST,
three screenshots, E16-E18 in the evidence log:

- **p1-nacl-web, acl-04426650b8a64f477 — 2 subnets:**
  p1-web-b subnet-0ca5116b6192f24a8 10.0.1.0/24
  us-east-1b, p1-web-a subnet-0e9bfcfe786d239d3
  10.0.0.0/24 us-east-1a. Screenshot:
  `screenshots/security-groups/step7-nacl-p1-nacl-web-2-web-subnets.png`
- **p1-nacl-app, acl-0ddcc2d0e9855da45 — 2 subnets:**
  p1-app-a subnet-02f9674b607c52d07 10.0.10.0/24
  us-east-1a, p1-app-b subnet-04440b9211f8322f7
  10.0.11.0/24 us-east-1b. Screenshot:
  `screenshots/security-groups/step7-nacl-p1-nacl-app-2-app-subnets.png`
- **p1-nacl-db, acl-054c237a420067341 — 2 subnets:**
  p1-db-b subnet-0f730dea656980038 10.0.21.0/24,
  p1-db-a subnet-01b906d224767a59a 10.0.20.0/24.
  Screenshot:
  `screenshots/security-groups/step7-nacl-p1-nacl-db-2-db-subnets.png`

The p1 default NACL, acl-02ad964f67e93bb07, now shows
0 explicit associations, as expected — all six p1
subnets have moved to the custom NACLs. The default
VPC NACL, acl-0cb13827f3b6182be, still has its 6
default subnets, untouched.

Inbound and outbound rules are NOT verified from
these screenshots — they show Subnet associations
only, not the Inbound/Outbound rules tabs. The list
view also shows a truncated "1 Inbo..." column for
each custom NACL, which may mean only 1 inbound rule
is present, not the 2-3 rules in the table above.
Check each NACL's Inbound rules and Outbound rules
tabs before Step 7 is marked complete, and check in
particular that p1-nacl-db has no 0.0.0.0/0 rule
anywhere.

Rules check, 2026-11-10, 15:50 CST, screenshot:
**p1-nacl-db, acl-054c237a420067341 — wrong.**
Inbound rules (1): only `* | All traffic | All |
All | 0.0.0.0/0 | Deny`. No allow rules at all.
That means the DB subnets currently block all
inbound traffic, even MySQL 3306 from the app tier.
Screenshot:
`screenshots/security-groups/step7-nacl-p1-nacl-db-inbound-only-deny.png`
(E19 in the evidence log.)

The other two NACLs show "1 Inbo..." in the list
too, so they are probably the same — only the *
Deny rule, no allow rules. Fix, still inside Step 7:
add the allow rules from the table above, for each
NACL, inbound and outbound, before the * Deny rule.
Rule numbers 100, 110, 120 are checked before *.
Do not delete the * Deny rule — it is the final
catch-all. After adding the rules, re-check each
NACL's Inbound and Outbound tabs.

Rules added, 2026-11-10, 16:05 CST, screenshots
E20-E21:

- **p1-nacl-web Outbound rules (4) — CORRECT:**
  100 HTTP 80 TCP 0.0.0.0/0 Allow; 110 HTTPS 443 TCP
  0.0.0.0/0 Allow; 120 Custom TCP 1024-65535
  0.0.0.0/0 Allow; * Deny. Screenshot:
  `screenshots/security-groups/step7-nacl-p1-nacl-web-outbound-correct.png`
- **p1-nacl-web Inbound rules (4) — ONE RULE WRONG:**
  100 HTTP 80 TCP 0.0.0.0/0 Allow; **110 HTTP 80 TCP
  0.0.0.0/0 Allow — should be HTTPS 443, not a
  second HTTP 80**; 120 Custom TCP 1024-65535
  0.0.0.0/0 Allow; * Deny. Screenshot:
  `screenshots/security-groups/step7-nacl-p1-nacl-web-inbound-110-wrong-http.png`
  Fix: Edit inbound rules, change rule 110 Type to
  HTTPS (443), Port 443.
- Banner in both screenshots: "You have successfully
  updated outbound rules for acl-054c237a420067341 /
  p1-nacl-db", so p1-nacl-db outbound was updated.
  List counts now: p1-nacl-db 3 inbound, p1-nacl-app
  3 inbound, p1-nacl-web 4 inbound — those counts
  match the expected allow + * Deny totals, but the
  app and db rule details have not been seen yet.

Web 110 fix, 2026-11-10, 20:19 CST, screenshot E22:
**p1-nacl-web Inbound rules (4) — now CORRECT:**
100 HTTP 80 TCP 0.0.0.0/0 Allow; 110 HTTPS 443 TCP
443 0.0.0.0/0 Allow; 120 Custom TCP 1024-65535
0.0.0.0/0 Allow; * Deny. Banner: "You have
successfully updated inbound rules for
acl-04426650b8a64f477 / p1-nacl-web". Screenshot:
`screenshots/security-groups/step7-nacl-p1-nacl-web-inbound-110-fixed-https.png`

p1-nacl-web is now fully correct, inbound and
outbound.

App and db rules, 2026-11-10, 20:21 CST,
screenshots E23-E26 — both CORRECT:

- **p1-nacl-app Inbound rules (3):** 100 HTTP 80
  TCP 10.0.0.0/16 Allow; 110 Custom TCP 1024-65535
  TCP 10.0.0.0/16 Allow; * Deny. Screenshot:
  `screenshots/security-groups/step7-nacl-p1-nacl-app-inbound-correct.png`
- **p1-nacl-app Outbound rules (4):** 100
  MySQL/Aurora 3306 TCP 10.0.0.0/16 Allow; 110
  HTTPS 443 TCP 0.0.0.0/0 Allow; 120 Custom TCP
  1024-65535 TCP 10.0.0.0/16 Allow; * Deny.
  Screenshot:
  `screenshots/security-groups/step7-nacl-p1-nacl-app-outbound-correct.png`
- **p1-nacl-db Inbound rules (3):** 100
  MySQL/Aurora 3306 TCP 10.0.0.0/16 Allow; 110
  Custom TCP 1024-65535 TCP 10.0.0.0/16 Allow;
  * Deny. Screenshot:
  `screenshots/security-groups/step7-nacl-p1-nacl-db-inbound-correct.png`
- **p1-nacl-db Outbound rules (2):** 100 Custom TCP
  1024-65535 TCP 10.0.0.0/16 Allow; * Deny.
  Screenshot:
  `screenshots/security-groups/step7-nacl-p1-nacl-db-outbound-correct.png`

p1-nacl-db has no 0.0.0.0/0 allow rule anywhere,
as designed.

Step 7 is complete.

---

## Step 8 — NAT Gateway, build-verify-delete in one session

### What we are doing

We are creating a NAT gateway in p1-web-a, giving
the app tier an outbound-only route to the internet
through it, verifying that route, and then deleting
the NAT gateway and releasing its Elastic IP in the
same session.

A NAT gateway lets private subnets reach out to the
internet, for updates and package downloads, without
letting the internet reach in. That is the difference
from the internet gateway in Step 5: the IGW route
in p1-rt-public lets traffic in and out for the web
tier; a NAT route in p1-rt-private lets app servers
start outbound connections, and only the replies
come back. No one can start a connection to an app
server through the NAT gateway.

Why p1-web-a, a public subnet: a NAT gateway must
live in a public subnet, one with a route to the
internet gateway, or it cannot reach the internet
itself. p1-web-a has that route, from Step 5.

Why only p1-rt-private: the app tier needs outbound
internet. The DB tier must never get an internet
route, so p1-rt-db stays local-only. The web tier
already has its IGW route, so p1-rt-public stays as
it is.

### Cost — read this first

A NAT gateway charges by the hour while it exists,
about $0.045 per hour in us-east-1, plus data
charges. That is small for an hour, and it adds up
if it is left running overnight. So this step is
build-verify-delete in one session: create it,
verify it, screenshot it, then delete it and release
the Elastic IP in the same sitting. Do not leave it
running, and do not leave the Elastic IP unattached
afterwards — an unattached Elastic IP also charges,
about $0.005 per hour.

The NAT gateway will be recreated later, in the
final deployed version, when there are app servers
that actually need it. This step is to prove the
route works and to record it as evidence.

### How to do it

Create the NAT gateway:

1. In the AWS Console, region us-east-1, open VPC >
   NAT Gateways.
2. Click **Create NAT gateway**.
3. **Name:** `p1-nat`
4. **Availability mode: choose Zonal, not Regional.**
   The form defaults to Regional - new, which hides
   the Subnet field and lets AWS spread the NAT
   gateway across AZs. Zonal is the one that lets
   you pick a specific subnet, which is what this
   step needs: one NAT gateway in p1-web-a.
   Screenshot of the Regional form with no Subnet
   field, 2026-11-10 20:24 CST:
   `screenshots/vpc-subnets/step8-create-nat-gateway-regional-no-subnet.png`
   (E27 in the evidence log.)
5. **VPC:** select `vpc-08694d42074a60709 (p1-vpc)`
6. **Subnet:** select `p1-web-a`
   (10.0.0.0/24, us-east-1a)
   **Connectivity type:** Public
   **Elastic IP allocation ID:** click **Allocate
   Elastic IP**
7. Click **Create NAT gateway**.
8. Wait for State to become **Available**. This takes
   a few minutes. Note the NAT gateway ID, it starts
   `nat-`, and the Elastic IP address it was given.

Add the route to the private route table only:

9. Open VPC > Route Tables, select `p1-rt-private`.
10. Open the **Routes** tab, click **Edit routes**,
    click **Add route**.
11. **Destination:** `0.0.0.0/0`
    **Target:** NAT Gateway, then select `p1-nat`
12. Click **Save changes**.
13. Do NOT add this route to p1-rt-public or to
    p1-rt-db.

Verify it:

14. On p1-rt-private, Routes should now be:
    - `10.0.0.0/16 | local | Active`
    - `0.0.0.0/0 | nat-... | Active`
15. On VPC > NAT Gateways, p1-nat should show State
    Available, Subnet p1-web-a, Connectivity type
    Public.
16. Take a screenshot of the NAT gateway list, and a
    screenshot of p1-rt-private Routes. Save them as
    `screenshots/vpc-subnets/step8-nat-gateway-p1-nat.png`
    and
    `screenshots/vpc-subnets/step8-route-table-p1-rt-private-nat-route.png`.

Delete it in the same session:

17. On VPC > NAT Gateways, select `p1-nat`, click
    **Actions > Delete NAT gateway**, type `delete`
    if it asks, and confirm. Wait for State to become
    **Deleted**.
18. Go back to VPC > Route Tables > `p1-rt-private`
    > Routes > **Edit routes**, remove the
    `0.0.0.0/0` route to the NAT gateway, and Save
    changes. p1-rt-private should be back to local
    `10.0.0.0/16` only. If the route is left pointing
    at a deleted NAT gateway, app traffic to the
    internet goes nowhere.
19. Open EC2 > Elastic IPs, select the Elastic IP
    that was allocated for p1-nat, click **Actions >
    Release Elastic IP addresses**, and confirm.
    Check the Elastic IPs list is empty afterwards,
    or at least that this address is gone.

### How to verify it

After step 16, before deleting: p1-nat Available in
p1-web-a, p1-rt-private has the 0.0.0.0/0 route to
it, p1-rt-public and p1-rt-db have no NAT route.

After steps 17-19: no NAT gateway in p1-vpc, no
0.0.0.0/0 route in p1-rt-private, no unattached
Elastic IP left over.

### Cost of this step

About $0.045 per hour while the NAT gateway exists,
plus a few cents of data if any, so well under $1
for a short verify-and-delete session. $0 afterwards,
once the NAT gateway is deleted and the Elastic IP
is released.

### Result, in progress

NAT route verified 2026-11-10, 20:29 CST,
screenshot E28:
**p1-rt-private, rtb-0fc6acae21be36950, Routes (2):**
- `0.0.0.0/0 | nat-018a4adf7596ed441 | Active`
- `10.0.0.0/16 | local | Active`
Banner: "Updated routes for rtb-0fc6acae21be36950 /
p1-rt-private successfully". Explicit subnet
associations 2, VPC p1-vpc. Screenshot:
`screenshots/vpc-subnets/step8-route-table-p1-rt-private-nat-route.png`

The NAT gateway's own list screenshot, with its
State, subnet, and Elastic IP, has not been seen
yet. The route being Active is evidence the NAT
gateway is up, but record its ID here:
**p1-nat, nat-018a4adf7596ed441**.

Delete in the same session, steps 17-19 above:
delete p1-nat, remove the 0.0.0.0/0 route from
p1-rt-private, release the Elastic IP. Step 8 is
NOT complete until that cleanup is confirmed.

Elastic IP found, 2026-11-10, 20:32 CST,
screenshot E29: EC2 > Elastic IP addresses (1),
**184.72.160.110, Public IP,
eipalloc-0eea63cbc614ec535**, no name, no
association shown. That is the p1-nat EIP.
Screenshot:
`screenshots/vpc-subnets/step8-elastic-ip-184-72-160-110.png`
To release it: click the checkbox at the left of
that row first, then Actions > Release Elastic IP
addresses, then confirm. The Release option only
appears after a row is selected.

EIP released, 2026-11-10, 20:33 CST, screenshot
E30: EC2 > Elastic IP addresses, "No Elastic IP
addresses found in this Region". Screenshot:
`screenshots/vpc-subnets/step8-elastic-ips-empty.png`

Route removed, 2026-11-10, 20:34 CST, screenshot
E31: **p1-rt-private, rtb-0fc6acae21be36950,
Routes (1):** `10.0.0.0/16 | local | Active` only.
No 0.0.0.0/0 route. Banner: "Updated routes for
rtb-0fc6acae21be36950 / p1-rt-private successfully".
Screenshot:
`screenshots/vpc-subnets/step8-route-table-p1-rt-private-local-only.png`

The EIP release in E30 also proves the NAT gateway
is deleted — an EIP attached to a NAT gateway
cannot be released while the NAT gateway exists.

Step 8 is complete. NAT gateway built, route
verified, then deleted with its route removed and
its Elastic IP released, in one session. No NAT
gateway and no unattached Elastic IP remain, so
no hourly NAT charge continues.

---

## Step 9 — Application Load Balancer and Auto Scaling

### What we are doing

We are putting real servers behind the load
balancer, so the chain from Step 6 actually
serves traffic: internet → ALB → app servers →
and, in Step 10, the database.

In order:
1. A target group, p1-tg-app, HTTP 80, in
   p1-vpc. This is the group the ALB forwards
   traffic to, and the group whose health checks
   decide whether a server is up.
2. A launch template, p1-lt-app, that says what
   each app server is: Amazon Linux 2023,
   t2.micro, security group p1-sg-app, and a
   start-up script that installs a web server
   and a simple test page.
3. An Auto Scaling group, p1-asg-app, that
   launches 2 servers from that template, one in
   p1-app-a and one in p1-app-b, and keeps 2
   running. If one fails its health check, Auto
   Scaling replaces it.
4. An Application Load Balancer, p1-alb,
   internet-facing, in p1-web-a and p1-web-b,
   with security group p1-sg-alb, and a listener
   on HTTP 80 that forwards to p1-tg-app.

The servers live in the app subnets, which are
private. They get no public IP. The only way in
is through the ALB, which is exactly what
p1-sg-app enforces: HTTP 80 only from p1-sg-alb.

### Cost — read this first

Unlike Steps 1-7, this step creates hourly
charges, and unlike Step 8, these are NOT
deleted in the same session. They stay up for
the Step 10 end-to-end test, then they are
deleted after the demo, unless Haileab
explicitly says to keep them up.

- ALB: about $0.0225 per hour, plus load
  balancer capacity units.
- 2 x t2.micro EC2: about $0.0116 per hour
  each, about $0.023 per hour together.
- Total about $0.046 per hour, about $1.10
  per day if left running. A few hours for the
  build and the Step 10 test is well under $1.
  Do not leave them running overnight without
  a decision to keep them.

### How to do it

Part A — Target group:

1. In the AWS Console, region us-east-1, open
   EC2 > Target Groups.
2. Click **Create target group**.
3. **Choose a target type:** Instances
   **Target group name:** `p1-tg-app`
   **Protocol:** HTTP, **Port:** 80
   **VPC:** select `p1-vpc`
   **Health check path:** `/`
   Leave the other health check settings at
   their defaults.
4. Click **Next**, then **Create target group**.
   Do not register targets manually — Auto
   Scaling will register the servers it
   launches.

Part B — Launch template:

5. Open EC2 > Launch Templates, click **Create
   launch template**.
6. **Launch template name:** `p1-lt-app`
   **Application and OS Images (AMI):** choose
   Amazon Linux 2023 AMI. Use the Quick Start
   Amazon Linux 2023 entry the console offers;
   do not pick an old Amazon Linux 2 AMI.
   **Instance type:** `t2.micro`
   If t2.micro is not offered, use `t3.micro`.
   **Key pair:** if you already have a key pair,
   select it. If not, click **Create new key
   pair**, name it `p1-key`, type RSA, format
   .pem, Create, and download the .pem file and
   keep it safe. You will not be able to
   download it again.
   **Security groups:** select `p1-sg-app` only.
   Do not select p1-sg-alb or the default group.
7. Scroll to **Advanced details > User data**,
   and paste exactly this:

```
#!/bin/bash
dnf install -y httpd
systemctl start httpd
systemctl enable httpd
echo "<h1>Hello from $(hostname)</h1>" > /var/www/html/index.html
```

8. Click **Create launch template**.

Part C — Auto Scaling group:

9. Open EC2 > Auto Scaling Groups, click
   **Create Auto Scaling group**.
10. **Auto Scaling group name:** `p1-asg-app`
    **Launch template:** select `p1-lt-app`,
    Version Default.
11. Click **Next**. **VPC:** `p1-vpc`.
    **Availability Zones and subnets:** check
    `p1-app-a` and `p1-app-b` only.
    Do not check a web subnet, and do not
    enable "Assign a public IP" — the app
    servers must stay private.
12. Click **Next**. **Load balancing:** check
    **Attach to an existing load balancer
    target group**, select `p1-tg-app`.
    **Health checks:** select ELB, or leave
    Health check type as ELB if it is already
    set.
13. Click **Next**. **Group size:**
    Desired capacity 2, Minimum capacity 1,
    Maximum capacity 2.
    Leave scaling policies off for this step.
14. Click through the remaining pages with
    their defaults, then **Create Auto Scaling
    group**.
15. Wait a few minutes. Open EC2 > Instances:
    2 instances should appear, both Running,
    both in p1-vpc, one in us-east-1a and one
    in us-east-1b, with no public IPv4 address.
    Open EC2 > Target Groups > `p1-tg-app` >
    Targets: both should become **Healthy**
    after the web server starts. This can take
    a few minutes; refresh the page.

Part D — Application Load Balancer:

16. Open EC2 > Load Balancers, click **Create
    load balancer**.
17. Click **Create** under Application Load
    Balancer.
18. **Load balancer name:** `p1-alb`
    **Scheme:** Internet-facing
    **IP address type:** IPv4
    **VPC:** select `p1-vpc`
    **Mappings:** check `us-east-1a` and select
    `p1-web-a`, check `us-east-1b` and select
    `p1-web-b`.
    **Security groups:** select `p1-sg-alb`
    only. Remove the default security group if
    it is selected.
    **Listener:** HTTP, Port 80, **Default
    action:** Forward to `p1-tg-app`.
19. Click **Create load balancer**.
20. Wait for State to become **Active**. This
    takes a few minutes. Copy the **DNS name**,
    it looks like
    `p1-alb-xxxx.us-east-1.elb.amazonaws.com`.

Part E — Test it:

21. Open `http://<ALB DNS name>` in a browser.
    You should see "Hello from ..." — the
    hostname of one of the two app servers.
    Refresh a few times; the hostname may
    change, because the ALB spreads traffic
    across both servers.
22. Take screenshots of: the Load Balancers
    list showing p1-alb Active with its DNS
    name, the Target Group Targets tab showing
    2 Healthy, and the browser page showing
    "Hello from ...". Save them as
    `screenshots/vpc-subnets/step9-alb-p1-alb-active.png`,
    `screenshots/vpc-subnets/step9-target-group-2-healthy.png`,
    and
    `screenshots/vpc-subnets/step9-alb-browser-test.png`.

### How to verify it

- Target group p1-tg-app, HTTP 80, p1-vpc,
  2 targets, both Healthy.
- Auto Scaling group p1-asg-app, Desired 2,
  Min 1, Max 2, subnets p1-app-a and p1-app-b,
  2 instances Running, no public IPs.
- Load balancer p1-alb, internet-facing,
  State Active, subnets p1-web-a and
  p1-web-b, security group p1-sg-alb,
  listener HTTP 80 forward to p1-tg-app.
- Browser test on the ALB DNS name returns
  the "Hello from ..." page.

### Cost of this step

About $0.046 per hour while the ALB and the 2
instances exist, about $1.10 per day. Keep
them only until the Step 10 end-to-end test
and demo are done, then delete the ALB, the
Auto Scaling group, and the instances.

### Result, in progress

ASG created, 2026-11-10, 20:52 CST, screenshot
E33:
- **p1-asg-app**, Status Updating capacity,
  Desired capacity 2, Scaling limits 1-2,
  Instances 0 at that moment, launching.
- Launch template **p1-lt-app**,
  lt-0707482f22b328e38, Version Default,
  AMI ami-09bf9dfeeb1e9adbc, Instance type
  **t3.micro** (used instead of t2.micro),
  Security group sg-0dc782d147f0112b /
  p1-sg-app, Key pair p1-key, Request Spot
  Instances No.
- Network: us-east-1a and us-east-1b,
  Subnet IDs subnet-02f9674b607c52d07
  (p1-app-a) and subnet-04440b9211f8322f7
  (p1-app-b).
- Date created Tue Nov 10 2026 20:52:05
  GMT-0600.
Screenshot:
`screenshots/load-balancer/step9-asg-p1-asg-app-created.png`

Load balancing page before creation, E32:
Attach to an existing load balancer, Choose
from your load balancer target groups,
p1-tg-app | HTTP selected. Screenshot:
`screenshots/load-balancer/step9-asg-load-balancing-p1-tg-app.png`

Instances and target health not yet verified.
Wait a few minutes, then check EC2 > Instances
for 2 Running, and Target Groups > p1-tg-app >
Targets for 2 Healthy. Then create the ALB,
Part D.

ALB DNS identified, 2026-11-10, 21:05 CST:
**p1-alb-1016513694.us-east-1.elb.amazonaws.com**
First browser test failed, but not because the
ALB failed — the URL was typed with angle
brackets, `http://<p1-alb-1016513694.us-east-1.elb.amazonaws.com>`,
into a Google search, and Google searched for
it instead of opening it. The `< >` are
placeholders only, never part of the URL.
Correct test: paste
`http://p1-alb-1016513694.us-east-1.elb.amazonaws.com`
into the browser address bar, not the Google
search box, and press Enter. Screenshot:
`screenshots/load-balancer/step9-alb-browser-test-google-search-wrong-url.png`
(E34 in the evidence log.)

ALB list screenshot, target health, and a
successful browser test have not been seen yet.
Step 9 is NOT complete until those are verified.

Targets unhealthy, 2026-11-10, 21:07 CST,
screenshot E35:
**p1-tg-app, Registered targets (2/2):**
- i-0a6b5ffd37407fd72, Port 80, us-east-1a,
  Unhealthy, Health checks failed
- i-0cf5ffed6d1780f8b, Port 80, us-east-1b,
  Unhealthy, Health checks failed
Screenshot:
`screenshots/load-balancer/step9-target-group-2-unhealthy.png`

Diagnosis: this is why the ALB test does not
work — with no healthy targets, the ALB has
nothing to forward to. The likely cause is the
user-data install: the launch template runs
`dnf install -y httpd` on first boot, and that
needs outbound internet. The app subnets have
no internet route, because Step 8 deleted the
NAT gateway and removed the 0.0.0.0/0 route
from p1-rt-private. So dnf could not download
httpd, httpd never started, port 80 never
opened, and the health check on `/` fails.
The security groups and NACLs are not the
likely cause — p1-sg-app allows HTTP 80 from
p1-sg-alb, and p1-nacl-app allows HTTP 80 and
ephemeral traffic from 10.0.0.0/16.

Fix, still inside Step 9:
1. Recreate the NAT gateway, p1-nat, in
   p1-web-a, Zonal, Public, Allocate Elastic
   IP, as in Step 8, and add 0.0.0.0/0 →
   p1-nat to p1-rt-private only.
2. Terminate both current instances, so Auto
   Scaling launches 2 fresh ones. User data
   runs only on first boot, so the existing
   instances will not install httpd just
   because the NAT gateway is back.
   EC2 > Instances, select i-0a6b5ffd37407fd72
   and i-0cf5ffed6d1780f8b, Instance state >
   Terminate instance. Auto Scaling, Desired
   2, will launch 2 replacements.
3. Wait for the replacements to boot with the
   NAT route in place, then check Target
   Groups > p1-tg-app > Targets: both should
   become Healthy.
4. Test the ALB DNS name again.
5. After the Step 10 test, delete the NAT
   gateway again, remove the 0.0.0.0/0 route
   from p1-rt-private, and release the Elastic
   IP, as in Step 8 cleanup. Do not leave the
   NAT gateway running overnight.

Recreated NAT verified, 2026-11-10, 21:20 CST,
screenshots E38-E39:
- NAT gateways (2): **nat-01d3c107223c205cf
  (p1-nat), Public, Available, Zonal** — the
  new one; nat-018a4adf7596ed441 (p1-nat),
  Public, Deleted — the old Step 8 one.
  Screenshot:
  `screenshots/vpc-subnets/step9-nat-gateways-new-available-old-deleted.png`
- Target group p1-tg-app: **Total targets 3,
  Healthy 0, Unhealthy 2, Unused 0, Initial 0,
  Draining 1.** The 1 Draining is an old
  terminated instance still deregistering;
  the 2 Unhealthy are the new replacements.
  Screenshot:
  `screenshots/load-balancer/step9-target-group-3-total-2-unhealthy-1-draining.png`
- At 21:20 CST that was only about 3 minutes
  after termination, so the new instances may
  still be booting and installing httpd. Wait
  a full 5-10 minutes from launch before
  calling it a failure.
- If still Unhealthy after 10 minutes, next
  suspect is DNS in p1-nacl-app: its outbound
  rules allow MySQL 3306 and HTTPS 443 and
  ephemeral ports, but no UDP 53 DNS rule.
  `dnf install` needs DNS to resolve the repo
  hostnames. Check the instance system log
  first (EC2 > Instances > select instance >
  Monitor and troubleshoot > Get system log)
  for the user-data / dnf error, then add a
  DNS rule if that is the failure.

DNS fix, given 2026-11-10, 21:27 CST, after
the replacements were still Unhealthy past
10 minutes:
p1-nacl-app is missing DNS, and NACLs are
stateless, so both directions are needed.
The existing ephemeral rules are TCP only,
so a UDP DNS reply is blocked too.
Add to **p1-nacl-app, acl-0ddcc2d0e9855da45**:
- Outbound, rule 130: Custom UDP, Port 53,
  Destination 10.0.0.0/16, Allow.
- Inbound, rule 120: Custom UDP, Port range
  1024-65535, Source 10.0.0.0/16, Allow.
Then terminate both current instances again,
so Auto Scaling launches fresh ones that run
user data with DNS working, wait 5-10
minutes, and check Target Groups > p1-tg-app
> Targets for Healthy. If still Unhealthy
after that, check the instance system log
before changing anything else.

Replacements launching, 2026-11-10, 21:38 CST,
screenshot E40:
Target group p1-tg-app: **Total targets 1,
Healthy 0, Unhealthy 1, Unused 0, Initial 0,
Draining 0.** Only 1 of the 2 replacements
has registered so far; the second is still
launching. Wait a full 5-10 minutes from
launch, then check again — total should be
2, and both should become Healthy if the
DNS fix worked. Screenshot:
`screenshots/load-balancer/step9-target-group-1-total-1-unhealthy-after-dns-fix.png`

Targets after DNS fix, 2026-11-10, 21:54 CST,
his paste, E41 (paste only, no screenshot):
- **i-00e10a16bb96c1321**, Port 80, us-east-1a,
  Unhealthy, Health checks failed, Launch
  Nov 10, 2026, 21:39, No override, Anomaly
  Normal.
- **i-06c5699107e9dbc39**, Port 80, us-east-1b,
  Unhealthy, Health checks failed, Launch
  Nov 10, 2026, 21:37, No override, Anomaly
  Normal.
Both are the post-DNS-fix replacements, and
both are still Unhealthy 15-17 minutes after
launch. DNS fix did not solve it on its own.
Next: verify the DNS NACL rules actually
saved, and read the instance system log for
the user-data / dnf / httpd error, before
changing anything else.

NACL rules verified, 2026-11-10, 21:56 CST,
his paste, E42 (paste only, no screenshot):
- p1-nacl-app **Inbound (4):** 100 HTTP 80
  TCP 10.0.0.0/16 Allow; 110 Custom TCP
  1024-65535 10.0.0.0/16 Allow; 120 Custom
  UDP 1024-65535 10.0.0.0/16 Allow; * Deny.
- p1-nacl-app **Outbound (5):** 100 MySQL
  3306 TCP 10.0.0.0/16 Allow; 110 HTTPS 443
  TCP 0.0.0.0/0 Allow; 120 Custom TCP
  1024-65535 10.0.0.0/16 Allow; 130 DNS
  (UDP) 53 UDP 10.0.0.0/16 Allow; * Deny.
Both DNS rules are present and Allow, as
designed. So the NACL is not the blocker.
Next: instance system log, to see the
user-data / dnf / httpd error.

System log, 2026-11-10, 21:57 CST,
i-00e10a16bb96c1321, IP 10.0.10.122, app-a,
his paste, E43 (paste only, no screenshot):
- Cloud-init ran, network up, route
  0.0.0.0 via 10.0.10.1, DNS resolver
  10.0.0.2.
- `dnf` failed: Curl error (28) Timeout was
  reached for
  https://al2023-repos-us-east-1-de612dc2.s3.dualstack.us-east-1.amazonaws.com/core/mirrors/...
  [Connection timed out after 30001 ms],
  for both the amazonlinux and
  kernel-livepatch repos.
- Ignoring repositories: amazonlinux,
  kernel-livepatch.
- No match for argument: httpd.
- Error: Unable to find a match: httpd.
- Failed to start httpd.service: Unit
  httpd.service not found.
- /var/www/html/index.html: No such file
  or directory.
- Cloud-init scripts-user failed, finished
  at 03:52:12 UTC, up 729.54 seconds.

Diagnosis: this is a timeout, not a DNS
failure — DNS resolved the repo hostname,
the TCP connection to S3 never completed.
The blocker is the **inbound** NACL return
path. p1-nacl-app inbound allows ephemeral
TCP 1024-65535 only from 10.0.0.0/16.
When the instance opens HTTPS 443 to a
public S3 address, the reply comes back
from that public address to an ephemeral
port, and the inbound NACL denies it
because its source is not in
10.0.0.0/16. Outbound HTTPS 443 to
0.0.0.0/0 was allowed, the return was not.
DNS worked because the resolver 10.0.0.2
is inside 10.0.0.0/16.

Fix, given 2026-11-10, 21:57 CST:
Add to **p1-nacl-app, acl-0ddcc2d0e9855da45,
Inbound, rule 130:** Custom TCP, Port range
1024-65535, Source 0.0.0.0/0, Allow.
Keep the existing rule 110, TCP ephemeral
from 10.0.0.0/16, as well. This only allows
return traffic on high ephemeral ports; no
service listens there, and p1-sg-app still
allows HTTP 80 only from p1-sg-alb.
Then terminate both current instances again
(i-00e10a16bb96c1321 and i-06c5699107e9dbc39),
so Auto Scaling launches fresh ones, wait
5-10 minutes, and check Target Groups >
p1-tg-app > Targets for Healthy, then test
the ALB.

Targets HEALTHY, 2026-11-10, 22:07 CST,
screenshot E44:
**p1-tg-app, Total targets 2, Healthy 2,
Unhealthy 0, Unused 0, Initial 0,
Draining 0, 0 Anomalous.** Load balancer
p1-alb, VPC vpc-08694d42074a60709 (p1-vpc),
Protocol HTTP: 80.
The inbound ephemeral return fix worked:
httpd installed, health checks pass.
Screenshot:
`screenshots/load-balancer/step9-target-group-2-healthy.png`

**Step 9 COMPLETE, 2026-11-10, 22:10 CST,
screenshot E45:**
Browser test on
http://p1-alb-1016513694.us-east-1.elb.amazonaws.com
shows:
**"Hello from ip-10-0-11-245.ec2.internal"**
That is an app server in p1-app-b,
10.0.11.0/24, us-east-1b — served through
the ALB, internet → ALB → app, as designed.
"Not Secure" in the address bar is expected:
the listener is HTTP 80, no TLS certificate
in this step.
Screenshot:
`screenshots/load-balancer/step9-alb-browser-test-hello-from-ip-10-0-11-245.png`
Note: an ALB list screenshot showing
p1-alb Active was not captured; the
browser test and the 2 Healthy targets
are the end-to-end proof the ALB works.
Refresh the page and the hostname may
change to the other app server, ip-10-0-10.x,
as the ALB spreads traffic.

Refresh confirmed, 2026-11-10, 22:11 CST,
screenshot E46:
**"Hello from ip-10-0-10-221.ec2.internal"**
That is the other app server, in p1-app-a,
10.0.10.0/24, us-east-1a. So both servers
have now served traffic through the ALB,
proving load balancing across both AZs.
Screenshot:
`screenshots/load-balancer/step9-alb-browser-test-hello-from-ip-10-0-10-221.png`

Step 9 is complete. Wait for his "go"
before Step 10.

---

## Step 10 — RDS MySQL in the DB tier, then end-to-end test, cleanup, and GitHub push

### What we are doing

We are creating the database, RDS MySQL, in the
DB tier only, then testing the whole chain
end to end, then deleting the hourly resources
and pushing the project to GitHub.

This is the last numbered step. After Step 10,
Serious 1 is done.

Part A, this task: create the DB subnet group
and the RDS instance, p1-db.
Part B, next: end-to-end test, ALB → app → DB.
Part C, last: cleanup, delete the hourly
resources, then the final evidence PDF and
the GitHub push.

### Why the DB lives only in the DB tier

RDS goes in p1-db-a and p1-db-b, 10.0.20.0/24
and 10.0.21.0/24, with route table p1-rt-db,
which has local 10.0.0.0/16 only and never gets
an internet route. Its security group is
p1-sg-db, MySQL 3306 only from p1-sg-app.
Its NACL is p1-nacl-db, MySQL 3306 in from
10.0.0.0/16 only, no 0.0.0.0/0 rule anywhere.
And Public access is No. So the database can
be reached only from an app server, on 3306
only, and nothing on the internet can reach
it, and it cannot reach the internet.

### Cost — read this first

RDS charges hourly while it exists, about
$0.017 per hour for db.t3.micro, plus about
$0.003 per hour for 20 GiB storage, about
$0.02 per hour total, about $0.48 per day.
Create it, verify it, test it, then delete
it after the demo, in Part C. Do not leave
it, the ALB, the Auto Scaling group, or the
NAT gateway running overnight without a
decision to keep them.

The NAT gateway nat-01d3c107223c205cf is
still up from the Step 9 fix, and the ALB
and 2 app servers are still up from Step 9.
Leave all three up for the Step 10 test,
then delete them in Part C.

### Part A — Create the DB subnet group and p1-db

Create the DB subnet group first:

1. In the AWS Console, region us-east-1,
   open RDS > Subnet groups.
2. Click **Create DB subnet group**.
3. **Name:** `p1-db-subnet-group`
   **Description:** `DB subnets for p1-vpc`
   **VPC:** select `p1-vpc`
4. **Availability Zones:** select
   us-east-1a and us-east-1b.
   **Subnets:** select `p1-db-a`
   (10.0.20.0/24) for 1a and `p1-db-b`
   (10.0.21.0/24) for 1b.
5. Click **Create**.

Then create the database:

6. Open RDS > Databases, click
   **Create database**.
7. **Engine options:** MySQL. Leave the
   engine version at the console default,
   do not pick an old version.
   **Templates:** Free tier, if it is
   offered, otherwise Dev/Test. Do not
   pick Production.
   **Creation method:** Standard create,
   not Easy create, so we control the VPC
   and security group.
8. **Settings:**
   - **DB instance identifier:** `p1-db`
   - **Master username:** `admin`
   - **Master password:** choose a strong
     password yourself and save it somewhere
     safe. Do NOT paste it in this chat.
     Confirm it in the second box.
9. **Instance configuration:**
   - **DB instance class:** `db.t3.micro`
   - **Storage:** 20 GiB, General Purpose
     SSD (gp2), leave storage autoscaling
     off.
   - **Multi-AZ DB instance:** No, do not
     create a standby instance.
10. **Connectivity:**
    - **Virtual private cloud (VPC):**
      select `p1-vpc`
    - **DB subnet group:**
      `p1-db-subnet-group`
    - **Public access:** No
    - **VPC security group:** Existing VPC
      security groups, select `p1-sg-db`
      only. Remove the default security
      group if it is selected.
    - **Availability Zone:** No preference
    - **Database authentication:**
      Password authentication
11. **Additional configuration:**
    - **Initial database name:** `p1db`
    - Leave backup, monitoring, and
      Performance Insights at their
      defaults. Do not enable Enhanced
      monitoring.
    - **Deletion protection:** leave it
      OFF, so we can delete the database
      in Part C.
12. Click **Create database**.
13. Wait for Status to become **Available**.
    This takes 5-10 minutes. Note the
    Endpoint address when it appears, it
    looks like
    `p1-db.xxxxx.us-east-1.rds.amazonaws.com`.

### How to verify Part A

On RDS > Databases, p1-db should show:
- Engine: MySQL
- Status: Available
- DB instance class: db.t3.micro
- VPC: p1-vpc
- Subnet group: p1-db-subnet-group
- Publicly accessible: No
- Security group: p1-sg-db only
- Endpoint: p1-db.xxxxx.us-east-1.rds.amazonaws.com,
  Port 3306

Take a screenshot of the Databases list, and
a screenshot of the p1-db details page showing
the endpoint, and save them as
`screenshots/database/step10-rds-p1-db-list.png`
and
`screenshots/database/step10-rds-p1-db-endpoint.png`.

Part A is done when p1-db is Available. Do
not go to Part B until it is Available.

**Part A COMPLETE, 2026-11-10, 22:28 CST,
screenshot E48:**
Banner: "Successfully created database
p1-db". Databases (3): database-1 Aurora
PostgreSQL Available, database-1-instance-1
Aurora PostgreSQL Available, and **p1-db,
Available, Role Instance, Engine MySQL
Community**. Screenshot:
`screenshots/database/step10-rds-p1-db-available.png`

### Part B — End-to-end test

What we test, and what we do not claim:
- p1-db details: endpoint, port 3306,
  VPC p1-vpc, subnet group
  p1-db-subnet-group, Publicly accessible
  No, security group p1-sg-db only.
- ALB still serves Hello, proving the
  web/app tier still works with the DB
  present.
- We do NOT claim a SQL query was run
  from an app server. The current app is
  a static Hello page with no DB code,
  and the app instances have no SSH or
  SSM access in this design, so there is
  no console way to run `mysql -h ...`
  from them. A real SQL test would need
  a DB client on the app servers, which
  is a follow-up, not part of this step.
  Record that limit honestly in the
  GitHub README, do not invent a DB
  connection test.

How to do Part B:
1. On RDS > Databases, click **p1-db**.
2. On the details page, record: Endpoint,
   Port 3306, Engine MySQL, DB instance
   class, VPC, DB subnet group, Publicly
   accessible No, Security group p1-sg-db,
   Availability Zone, and Status Available.
   Screenshot the details page as
   `screenshots/database/step10-rds-p1-db-endpoint.png`.

p1-db details verified, 2026-11-10, 22:30
CST, screenshot E49:
- DB Identifier: p1-db, Status Available,
  Role Instance, Engine MySQL Community,
  CPU 6.89%, Current activity 0 Connections.
- **Class: db.t4g.micro** — correction:
  the console Free tier gave db.t4g.micro,
  not db.t3.micro as planned. Record
  db.t4g.micro, do not claim db.t3.micro.
- **Region & AZ: us-east-1b** — the
  instance landed in 1b, in p1-db-b.
- **Endpoint:
  p1-db.ci5cw8aia5ax.us-east-1.rds.amazonaws.com,
  Port 3306**, user admin, connection
  command in the screenshot:
  `mysql -h p1-db.ci5cw8aia5ax.us-east-1.rds.amazonaws.com -P 3306 -u admin -p --ssl-mode=VERIFY_IDENTITY --ssl-ca=./global-bundle.pem`
- Internet access gateway: Disabled.
  IAM Authentication: Disabled.
  Connected compute resources: 0.
- Screenshot:
  `screenshots/database/step10-rds-p1-db-endpoint.png`
- VPC, DB subnet group, Publicly
  accessible, and security group are
  NOT visible in this screenshot — they
  are on the Configuration tab. Check
  that tab next, before calling Part B
  done, to confirm Publicly accessible
  No, VPC p1-vpc, subnet group
  p1-db-subnet-group, and security group
  p1-sg-db only.

Configuration tab, 2026-11-10, 22:30 CST,
screenshot E50:
- DB instance ID p1-db, Engine version
  **8.4.11**, RDS Extended Support
  Disabled, License General Public
  License, Option groups
  default:mysql-8-4 In sync, DB instance
  parameter group default.mysql8.4
  In sync.
- **DB name: – (blank).** Correction:
  no initial database was created, so
  do NOT claim a database named p1db
  exists in p1-db.
- ARN arn:aws:rds:us-east-1:762049038082:db:p1-db.
  Created time November 10, 2026, 22:22
  (UTC-06:00).
- **Deletion protection: Disabled** —
  good, we can delete it in Part C.
- Instance class db.t4g.micro, vCPU 2,
  RAM 1 GB, Master username admin,
  IAM DB authentication Not enabled,
  Multi-AZ No, Secondary Zone –.
- Primary storage: Encryption Enabled,
  AWS KMS key aws/rds, Storage type
  General Purpose SSD (gp2), Storage
  **20 GiB**, Provisioned IOPS –,
  Storage throughput –.
- **Storage autoscaling: Enabled,**
  Maximum storage threshold 1000 GiB.
  Correction: the console left this on,
  it was not turned off as planned.
- Monitoring: Database Insights -
  Standard, Database counter metrics
  Disabled, **Enhanced Monitoring:
  Enabled**, Granularity 60 seconds,
  Monitoring role
  arn:aws:iam::762049038082:role/rds-monitoring-role.
  Correction: Enhanced Monitoring was
  left on by the console default.
- Architecture: Non-multitenant.
- Screenshot:
  `screenshots/database/step10-rds-p1-db-configuration.png`
- VPC, DB subnet group, Publicly
  accessible, and security group are
  STILL not visible in this screenshot
  — they are on the Connectivity &
  security tab, below the fold. Scroll
  down there to confirm them before
  calling Part B done.
3. In a browser, open
   http://p1-alb-1016513694.us-east-1.elb.amazonaws.com
   again. It should still show
   "Hello from …". Screenshot it as
   `screenshots/load-balancer/step10-alb-test-with-db.png`.
4. Part B is done when both are verified.
   Then go to Part C, cleanup.

ALB test with DB, 2026-11-10, 22:32 CST,
screenshot E51:
**"Hello from ip-10-0-10-221.ec2.internal"**
on http://p1-alb-1016513694.us-east-1.elb.amazonaws.com,
app-a server, 10.0.10.221, us-east-1a.
The ALB still serves traffic with p1-db
present. Screenshot:
`screenshots/load-balancer/step10-alb-test-with-db.png`
Connectivity & security scroll, to confirm
VPC p1-vpc, Publicly accessible No, and
security group p1-sg-db only, is still
outstanding — send that screenshot before
deleting p1-db in Part C, or Part B will
be recorded with those three fields set
at creation but not re-verified in a
screenshot.

**Security group WRONG, found 2026-11-10,
22:33 CST, screenshot E52 — Part B NOT
complete as designed:**
Security group rules (2) on p1-db:
- **default (sg-07c41c74bd4e09c2f)** —
  EC2 Security Group - Inbound —
  sg-07c41c74bd4e09c2f
- **default (sg-07c41c74bd4e09c2f)** —
  CIDR/IP - Outbound — 0.0.0.0/0
That is the VPC default security group,
NOT **p1-sg-db, sg-063e10e3231772a8b**.
The default group was not removed at
creation, and p1-sg-db was not attached.
Why it matters: the default group's
inbound rule allows only traffic from
itself, and the app servers carry
p1-sg-app, not the default group, so
the app tier cannot reach p1-db on
3306 through this group. The Step 6
chain — DB on 3306 only from p1-sg-app
— is broken at the RDS level, even
though p1-sg-db itself is correct.
Other details in the same screenshot:
Internet access gateway Disabled, IAM
Authentication Disabled, Connected
compute resources (0), Replication (1)
p1-db, Instance, us-east-1b.
Screenshot:
`screenshots/database/step10-rds-p1-db-security-group-wrong-default.png`

**Fix, before Part C — superseded, see
below: the Modify fix will NOT work,
because the DB is in the wrong VPC.**

**Bigger problem found, 2026-11-10,
22:36 CST, Modify page, screenshot E53:**
DB subnet group on the Modify page:
**default-vpc-0a0cff632591d850c**.
That is the default VPC's subnet group,
VPC ID vpc-0a0cff632591d850c, 172.31.0.0/16.
So **p1-db was created in the DEFAULT
VPC, not in p1-vpc**, and in the default
subnets, not p1-db-a/b.
That explains the wrong SG in E52: the
default VPC's default SG was used, and
p1-sg-db (a p1-vpc group) was never
attached.
A DB instance's VPC and subnet group
**cannot be changed by Modify**. The
Security group dropdown on Modify will
only show default-VPC groups, not
p1-sg-db. So the Modify-SG fix above
will not work.
Screenshot:
`screenshots/database/step10-modify-db-subnet-group-default-vpc.png`

**Correct fix: delete p1-db and recreate
it, in p1-vpc:**
1. On the Modify page, click **Cancel**
   — do NOT save any Modify change.
2. RDS > Databases > select **p1-db** >
   Actions > **Delete**. Uncheck
   "Create final snapshot", confirm.
   Wait for it to disappear.
3. Create database > **Full configuration**
   again, same settings as before:
   MySQL, p1-db, admin, db.t3.micro
   (console may give db.t4g.micro again
   — record whichever it gives),
   20 GiB gp2, Multi-AZ No, deletion
   protection OFF.
4. **Connectivity — check these three
   before clicking Create, this is the
   part that went wrong:**
   - VPC: **p1-vpc, vpc-08694d42074a60709**
     — NOT the default VPC.
   - DB subnet group: **p1-db-subnet-group**
     — NOT default-vpc-0a0cff632591d850c.
     Picking this group is what puts the
     DB in p1-vpc, in p1-db-a/b.
   - Public access: **No**
   - VPC security group: **p1-sg-db only**,
     remove the default group if selected.
5. Create, wait for Available, then
   re-verify: endpoint, class, AZ,
   VPC p1-vpc, subnet group
   p1-db-subnet-group, Publicly
   accessible No, SG p1-sg-db only.
   Screenshot each, then do the ALB
   test again, then Part C cleanup.

DB subnet group created, 2026-11-10, 22:16
CST, screenshot E47:
Banner: "Successfully created
p1-db-subnet-group. View subnet group".
Screenshot:
`screenshots/database/step10-db-subnet-group-created.png`
Note in the same screenshot: Databases (2)
already exist in this account, **database-1**
and **database-1-instance-1**, both Aurora
PostgreSQL, both Available. Those are
pre-existing, not part of Serious 1 — do
NOT modify or delete them.
Create database dropdown in the screenshot:
Express configuration, **Full configuration**,
Restore from S3. Click **Full configuration**
— that is the Standard create form, with
all the fields in the full configuration
list above. Do NOT click Express configuration.

### Evidence pack

All screenshots so far are labelled by stage, with what
was done, what each shows, and whether it passed or
needed a fix, in:
`Serious-1-Evidence-Pack-Steps-1-4.pdf` (8 pages, A4).
It covers Steps 1-4, E01-E11, and is ready to upload to
GitHub with the project README. New screenshots from
later steps will be added to a new version of the pack.

---

## Final status — ended 2026-11-10, 22:37 CST, at Haileab's direction

Haileab: "its foine just use the last successful screenshot and end it there and push it to my repository with proper description and all."

So Serious 1 ends here, with the last successful test as the end point:
**Step 10, Part B ALB test, 2026-11-10 22:32 CST, screenshot E51 — "Hello from ip-10-0-10-221.ec2.internal"**, the ALB still serving traffic with p1-db present.

What is complete and verified:
- Steps 1–9 complete: p1-vpc 10.0.0.0/16 in us-east-1, 6 subnets in 2 AZs, 3 route tables, IGW route on public only, chained security groups ALB → app → DB, 3 NACLs, NAT build-verify-delete in Step 8, ALB + Auto Scaling with 2 Healthy targets, load balancing proven across both AZs (10.0.10.221 and 10.0.11.245).
- Step 10, Part A: DB subnet group p1-db-subnet-group created; RDS p1-db created and Available, MySQL Community 8.4.11, db.t4g.micro, 20 GiB gp2, endpoint p1-db.ci5cw8aia5ax.us-east-1.rds.amazonaws.com:3306, AZ us-east-1b, deletion protection Disabled.

What is NOT complete, and is recorded honestly, not hidden:
- **p1-db is in the WRONG VPC.** It was created in the default VPC (172.31.0.0/16, subnet group default-vpc-0a0cff632591d850c), not in p1-vpc, not in p1-db-a/b. See E52/E53.
- **p1-db is on the wrong security group.** It is attached to the default SG sg-07c41c74bd4e09c2f, not p1-sg-db sg-063e10e3231772a8b. The app tier cannot reach it on 3306 through that group.
- **No SQL query was run from an app server.** The app is a static Hello page with no DB code, and the app instances have no SSH/SSM access. Do NOT claim a database connection test succeeded.
- **No initial database named p1db was created.** DB name is blank on the Configuration tab.
- Storage autoscaling and Enhanced Monitoring were left Enabled by the console defaults, not turned off as planned.
- The fix — delete p1-db and recreate it in p1-vpc with p1-db-subnet-group, Public access No, and p1-sg-db only — was NOT done, at Haileab's direction to end here. It is documented above, in the Step 10 fix section, for a later rebuild.
- Part C cleanup was NOT done in this session. As of the end of this build, the hourly resources are still up: ALB p1-alb + 2 app servers, NAT gateway nat-01d3c107223c205cf, and RDS p1-db. Delete them to stop the charges — see the cleanup steps in the Step 10 / Part C section of the chat record. Do NOT delete the pre-existing Aurora databases database-1 / database-1-instance-1, or the $0 network (VPC, subnets, route tables, IGW, security groups, NACLs) unless directed.

Evidence: E01–E53, screenshots in `screenshots/`, full index and descriptions in `Serious-1-Evidence-Pack-Final.pdf`.
