# Import notes for developers

While most of the import processes are documented over in the features / importing area, this document houses notes specifically targeted to developers.

## Upload validation

All multipart import uploads are validated through `backend.app.core.file_uploads` before they are parsed or persisted. Use `validate_upload(file, kind=UploadKind.ZIP)` for profile ZIP imports that are consumed in memory, and `save_validated_upload(file, kind=..., upload_dir=..., filename=...)` for uploads that are written to disk.

Activity uploads use server-generated filenames and `UploadKind.ACTIVITY` or `UploadKind.GZIP`; decompressed gzip payloads are re-validated as `UploadKind.ACTIVITY` before parsing. Validation failures are raised as `HTTPException` responses whose `detail` includes a human-readable `message` and, when provided by `safeuploads`, a machine-readable `code`.

## Bulk import

When items are imported either through a bulk import or Strava bulk import, the dictionary "import_info" is created for the activity to record information on the import.

The import_info dictionary should include at least the following fields:
* imported (boolean)
* import_source (str) - e.g., "Strava bulk import" or "Basic bulk import"
* strava_activity_id (int) - holds Strava's internal activity ID for Strava activities when imported from a bulk Strava import
* import_ISO_time (str) - an ISO formatted string holding the time of import.  This will be the time the entire improt was triggered, and should be the same for all files of a single bulk import.

If this dictionary exists for an activity, then the file was imported with one of those two functions (after this routine was added, likely v0.18.0).  Checking the "imported" field of the import_info dict can double-check this.

These fields allow determination of when files were imported (to facilitate future creation of the ability to roll back an import), and also allow separation of imported Strava activities from Strava activities added via linking with Strava as a service.
