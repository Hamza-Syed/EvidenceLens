# EvidenceLens development

After completing and validating requested changes, commit and push them to the
configured EvidenceLens GitHub remote. The user has authorized this as the normal
completion workflow. Preserve remote history; do not force-push.

Keep secrets, uploaded PDFs, virtual environments, dependency directories, build
outputs, and model caches out of commits. Keep the sample generators and fixtures.

Preserve document-scoped verification and page citations. Retrieval similarity is
candidate ranking, never proof or confidence. Run the backend tests, TypeScript
validation, and frontend production build for completed feature milestones.
