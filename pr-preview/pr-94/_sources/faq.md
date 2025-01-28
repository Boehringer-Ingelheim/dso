# FAQ

## Can I use dvc to track files that are outside the repository?

Yes, this is possible by specifying an absolute path to that file. However, note that DVC will only _track_ but not _version_ that file. I.e. updating that files will invalidate the cache for `dvc repro`, but it will not be updated by `dvc pull` / `dvc checkout`.
