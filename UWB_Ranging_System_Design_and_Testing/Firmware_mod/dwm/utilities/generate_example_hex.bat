::Please set the variable "example" with the target example name
::Please set the variable "fw2_path" to the binary image that was generated with SES
SET example_name=dwm-simple
SET fw2_path=..\examples\dwm-simple\Output\linker\dwm-simple_fw2.bin

::Do not modify the paths below as they are reference binaries:
SET fw1_path=..\recovery\dwm-core_fw1.bin
SET sfd_path=..\recovery\s132_nrf52_3.0.0_softdevice.hex
SET btl_path=..\recovery\bootloader_s132.bin

:: Current path
SET mypath=%~dp0


IF EXIST %fw2_path% (
	
	objcopy -I binary %btl_path% -O ihex bl.hex --change-addresses 0x1f000
	objcopy -I binary %fw1_path% -O ihex fw1.hex --change-addresses 0x22000
	objcopy -I binary %fw2_path% -O ihex fw2.hex --change-addresses 0x44000
	mergehex -m %sfd_path% fw1.hex fw2.hex -o argo-out0.hex
	mergehex -m bl.hex argo-out0.hex -o "dwm1001_%example_name%.hex"
	del bl.hex
	del fw1.hex
	del fw2.hex
	del argo-out0.hex

	MOVE "dwm1001_%example_name%.hex" "..\examples\%example_name%\Output\dwm1001_%example_name%.hex" 
	echo The combined image was sucesfully created :
	echo %mypath:~0,-11%\examples\%example_name%\Output\dwm1001_%example_name%.hex &pause
	
	
	
) ELSE (
	start "" cmd /c "echo The FW2 path is not valid : %fw2_path% &echo(&pause"
)