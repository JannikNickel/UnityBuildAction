## UnityBuildAction

### `builder`
Github Action to build Unity projects using the Unity CLI on a self hosted windows action runner.

### `bootstrapper`
Contains another action and some scripts to reset and start up the windows runner from a linux runner within the same network as the windows runner.

### `cache` & `cache/restore`
Actions to cache and restore a folder to / from an S3 server. Unfortunately the default cache action doesnt support custom urls yet and some other solutions need binary patching which is a possible source for problems with updates:
https://github.com/falcondev-oss/github-actions-cache-server
