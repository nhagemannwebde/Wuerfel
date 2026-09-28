[app]

# (str) Title of your application
title = Würfelspiel 10000

# (str) Package name
package.name = wuerfelspiel

# (str) Package domain (needed for android/ios packaging)
package.domain = com.dice

source.dir = .
source.include_exts = py,png,jpg,kv,atlas

# (str) Application versioning
version = 0.1

# (list) Application requirements
requirements = python3,kivy

# (str) Supported orientation
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (list) Permissions
android.permissions = INTERNET

# (int) Android API to use
android.api = 31

# (int) Minimum API
android.minapi = 21

# (str) Android NDK version to use
android.ndk = 25b

# (str) Android SDK version to use
android.sdk = 33

android.private_storage = True
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1