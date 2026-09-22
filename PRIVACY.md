# Privacy model

Source images, PDFs, videos and audio stay on the local Mac. Apple Vision, PDFKit and AVFoundation extract text, previews and sampled video frames locally.

TypeSafe receives the configured filename, immediate folder name and redacted extracted text used for category and title selection. The organizer removes common email addresses, phone numbers, long numeric identifiers and credential-shaped values before that request. Review the redaction rules for your own data before enabling classification.

The optional descriptive-metadata pipeline sends structured text evidence to the selected Codex model and sends the resulting redacted descriptions to TypeSafe for controlled topic selection. It does not send source media. Metadata and model responses are stored under the local state directory and are excluded from Git by default.

The generated dashboard contains filenames, absolute local paths, descriptions and a local authentication token. It is intentionally excluded from Git. The dashboard helper binds only to `127.0.0.1` and checks the token on every action.
