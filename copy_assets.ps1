$dist = "dist"

# Clean up assets and sounds in dist if they exist to avoid nesting
if (Test-Path "$dist\assets") { Remove-Item "$dist\assets" -Recurse -Force }
if (Test-Path "$dist\sounds") { Remove-Item "$dist\sounds" -Recurse -Force }

if (!(Test-Path $dist)) { mkdir $dist }

Write-Host "Copying assets to $dist..."
Copy-Item -Recurse -Path "assets" -Destination $dist -Force

Write-Host "Copying sounds to $dist..."
Copy-Item -Recurse -Path "sounds" -Destination $dist -Force

# Copy generated cloud voices to simulate downloaded state
# We want cloud folder inside dist/sounds
# dist/sounds already exists now.
# So Copy-Item "cloud" "dist/sounds" will create "dist/sounds/cloud"
Write-Host "Copying cloud voices..."
Copy-Item -Recurse -Path "cloud" -Destination "$dist\sounds" -Force

Write-Host "Packaging complete. Check $dist folder."
