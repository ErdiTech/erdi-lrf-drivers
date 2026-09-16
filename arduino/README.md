# Arduino library — moved to a standalone repository

The `ErdiLRF` Arduino library that used to live only in this `arduino/`
subfolder is now also maintained as a standalone repository:

**https://github.com/yu911517778-a11y/ErdiLRF**

This was done on 2026-09-17 so the library could be registered with the
[Arduino Library Manager](https://github.com/arduino/library-registry/pull/9133)
(merged the same day) and the [PlatformIO Registry](https://registry.platformio.org)
(`erdi-tech/ErdiLRF`) — both require a dedicated, tag-releasing repository
rather than a subfolder of a mono-repo.

The code in this `arduino/ErdiLRF/` directory is left in place (unchanged,
still tested) so existing `--git-url ...#main:arduino/ErdiLRF` installs and
CI jobs referencing this mono-repo keep working. New installs, issues, and
releases should go through the standalone repo above; its README documents
installation, supported models, and usage examples.
