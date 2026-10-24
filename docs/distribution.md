---
title: "Distribution and handoff"
---

OrcaPen means an orca's pen, inspired by the cute story of an orca and a penguin.
A person who loves that idea develops this open superconducting PDK, distributed
as `orcapen-sc-pdk`; Python imports and the registered PDK use `orcapen_sc_pdk`.
The repository is [OrPenStrike/orcapen-sc-pdk](https://github.com/OrPenStrike/orcapen-sc-pdk),
with [documentation on GitHub Pages](https://orpenstrike.github.io/orcapen-sc-pdk/).

## Current local candidate

Project-authored public content uses the [MIT License](../LICENSE). See
[License scope](../LICENSING.md) for private-material exclusions and
accidental-disclosure handling, and [Third-party notices](../THIRD_PARTY_NOTICES.md)
for separate source attributions. These notices do not revoke previously valid
licenses or replace third-party terms.

`0.1.0.dev2` is a local candidate, not a registry release. Review the versioned
wheel and its source identity, resource inventory and digest before handing it
to a consumer. An ordinary wheel is the handoff artifact; consumers do not need
this development workspace or an editable checkout to read its bundled usage
resources or construct public cells.

Use the [Get Started](getting-started.md) local-wheel installation and activation
example. A successful installation is not fabrication, solver or scientific
qualification. Source-only notebook revisions do not reattribute retained outputs
to the renamed package; those outputs keep their original run provenance.

## GDSFactory+ consumer actions

GDSFactory+ 2.1.458 Project Settings offers three separate actions:

- **Install <configured PDK> from registry** installs the project's configured
  PDK. In a private project that may be its private PDK, not this public base.
- **Install from .whl** selects an already-built wheel for local installation.
  Use the reviewed OrcaPen candidate artifact when that consumer change is authorized.
- **Upload PDK to registry** selects one or more already-built wheels and uploads
  them through Twine to the authenticated organization's GF+ PyPI-compatible
  registry. It does not build the wheel or publish it to public PyPI.

Keep the consumer's own project and private base PDK intact. Updating its OrcaPen
dependency and removing editable-source configuration require separate consumer-owner
approval. This local candidate does not migrate a live GF+ server. Neither wheel
installation nor restarting is claimed to resolve the existing factory-index issue.
The core package does not supply a live viewer; its package factories remain
distinct from a consumer's project configuration.

## Future organization-registry publication

After owner review and explicit publication authorization, upload the reviewed,
versioned wheel to the organization's chosen registry and retain its exact digest
and source identity. No upload has occurred in this candidate workflow, and this
guide makes no claim of PyPI availability or of a public-index install command.
Registry credentials, access policy and publication remain with the registry owner.

Migration of existing consumer environments, import references or private base
PDKs is future consumer-owner work. Do not replace a private PDK, alter its
dependencies or migrate its layouts merely because this public candidate has
been renamed.
