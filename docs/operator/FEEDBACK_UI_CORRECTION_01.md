# Feedback UI Correction 01

This change presents hosted answer feedback in an inline disclosure. It retains
the existing feedback storage, identity, authorization and export behavior. It
does not change Research or Answer behavior, provider routing, or deployment
configuration. SQLite remains at schema 6; this same-schema application update
does not require another schema-migration receipt.

With JavaScript, feedback actions preserve the other drafts and completion
polling defers a reload while feedback is being edited. Native forms also submit
and remove feedback without JavaScript, but their full-page navigation cannot
preserve unsent drafts in other forms. Validation retains the submitted feedback
text. This existing no-JavaScript limitation is not changed by the disclosure.

## Release handoff

After the change is reviewed and merged, and only when deployment is separately
authorized, select the exact reviewed release revision. Prepare a fresh source
directory from that revision, not from the ordinary checkout. For example, set
`$releaseSha` to that full revision and choose unused paths under `C:/tmp`:

```powershell
$archive = 'C:/tmp/scryraven-release.tar'
$releaseDir = 'C:/tmp/scryraven-release-source'
New-Item -ItemType Directory -Path $releaseDir -ErrorAction Stop | Out-Null
git archive --format=tar --output=$archive $releaseSha
if ($LASTEXITCODE -ne 0) { throw 'git archive failed' }
tar -xf $archive -C $releaseDir
if ($LASTEXITCODE -ne 0) { throw 'archive extraction failed' }
```

Inspect the archive and extracted source before upload. Follow the existing
application-release procedure in `PRIVATE_DOGFOOD_DEPLOYMENT_01.md`: explicitly
select the existing Railway project, service and environment and use
`railway up <archive-directory> --path-as-root`. Record the source SHA, image
digest when available, dependency versions and deployment ID. This command
deploys immediately; it is not a preparation-only step. No Railway access,
production database access, credentials or deployment is part of this phase.
