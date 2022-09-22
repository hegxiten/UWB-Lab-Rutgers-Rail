## From a reference application to a custom application

This folder contains a patch to the the Reference iOS Application to add an extra functionality, such as

- Start/Stop button
- displaying of 2D and 3D arrow
- displaying measurements of an angle to the accessory



## Reference iOS application and documentation

The Reference iOS application to demonstrate Nearby Interaction with Third party accessory can be found by the link below:

https://developer.apple.com/documentation/nearbyinteraction/implementing_spatial_interactions_with_third-party_accessories

The documentation for Nearby Interaction can be found here: 

https://developer.apple.com/nearby-interaction/



## Applying patch for the Original iOS App

1. Download the original application
2. Copy the patch to the same level as a root folder of the original application
3. In the Terminal execute the following command
`git apply --reject --whitespace=fix Qorvo_NI_3D_patch.diff`



## Build & Run

To be able to build and run the project it is required to select an appropriate Apple Developer credentials:

1. Click on the project file and in its options go to "Signing & Capabilities" and select your Team
2. On the top bar select your test device (iPhone 11/12)

To build and run press the "play" button on the left upper corner of XCode.



/Signed

Sep 08 2021