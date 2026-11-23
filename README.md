# AVIO Robotics

**Autonomous Intelligence for the Skies**

Independent, early-stage robotics initiative exploring three connected pillars:

1. **AI Navigation & Computer Vision** — perception, localization, mapping, and path planning.
2. **Swarm Robotics** — coordination, shared perception, and collaborative mission planning.
3. **Autonomous Infrastructure Inspection** — inspection workflows and data analysis.

> **Project status:** early-stage concept and website. Capabilities, commercial traction, legal incorporation, and hardware performance have not been validated or claimed.

## Website

The website is a static, responsive HTML/CSS/JavaScript site. No build system is required.

- Homepage: `index.html`
- Illustrations and favicon: `assets/`
- Privacy and accessibility: `privacy.html`, `accessibility.html`
- Sitemap and crawler configuration: `sitemap.xml`, `robots.txt`

### Run locally

Open `index.html` in a browser, or run `python3 -m http.server 8000` from the repository root and open http://localhost:8000.

### Publish on GitHub Pages

Go to **Settings → Pages → Build and deployment**. Select **Deploy from a branch**, choose **main** and **/(root)**, then save. The expected address is https://panagiotagrosdouli.github.io/AVIO/ once the build is published. This does not guarantee GitHub Pages is already enabled.

### Contact

The website contact form does **not** transmit data or send messages. It prepares a message for the visitor to copy. GitHub Issues are an alternative public discussion channel; avoid posting private information.

## Engineering direction

Build and benchmark in simulation before any field trials. Any physical operations need appropriate safety, legal, and regulatory review. AVIO is independent of V4RL and SkEyes; no partnership is implied.

## Contributions

Discussions, reproducible bug reports, and thoughtful technical proposals are welcome through GitHub Issues. No open-source license has been selected yet, so repository visibility does not grant unrestricted reuse of its contents.
