# Clean Slate Release Plan

- 1.) we need to remove all git tags from the repository
- 2.) we need to orphan main, to clear the commit history
- 3.) all waveshare periferal code needs to be attributed to Waveshare and list the activite source license. Apache for the rtc driver, the temp sensor code is unlicensed, but it originally came from, Waveshare and the data sheet. we took parts of the epaper display code from the unlicensed repo aswell. everything else was basically wrote by us. to cover our butts, all waveshare code should be licensed as Apache. the unlicensed code may have been a simple mistake by waveshare during publishing. or the unlicensed code could have been derived from an existing repo that I'm unaware of. the commonality in waveshares repository is Apache, so that's why we assume, Apache.
- 3.b) our code is being released as MIT, and all assets (if applicable) are released as Creative Commons (I think, I'll need to double check the lic file).
- 4.) we need to move all bsp examples except for the main test suit and boilerplate code into a sub directory labeled bsp_samples. this is needed to organize the examples folder.
- 5.) we need to clean and check all bsp_samples example code to ensure the project files are properly set up, and ready to compile. (if 'you' think it's needed, we can add a readme to each example project)
- 6.) we need to remove the board manifest json, the json is not used by idf, this makes the json a lose end that must be cut. the root sdkconfig needs copied into all example dirs. all build dirs, logs, managed components, need to be removed. we do not have to compile the sample code in the samples directory, but we need to stage it so that me/you, can compile it if needed.
- 7.) to facilitate development with the bsp, we need to include a boilerplate example in the examples directory. we need to set up the full lifecycle for the user and assign startup and shutdown callbacks to the power button. everything else can be empty. audio is not needed, sleep is not needed, we can compile without the thingsboard bsp layer. at minimum, maybe include a batt/temp/button readout on the display that updates every 5 seconds, as the main supper loop. main should just be a while look calling our demo function, and a 5sec delay.
- 8.) we need to remove the bsp_asset backup source file pair, as it's no longer needed.
- 9.) we need to regen the API doc after changing the version string to v1.0.0 as per our clean slate, the version also needs changed in the readme file as well. Or create a singleton version file that gets read by the readme markdown, and or version.h file, for easy versioning and maintenance.
- 10.) we need to look over the markdown docs to make sure they accurately reflect the current state of the code.
- 11.) we need to double check all doxygen comments before generating the API doc. this means inspecting every the .c/.h to ensure HUMIDYNE LABS, Humiditron, and Gemini are attributed to development (you helped A LOT, and deserve recognition), as well as waveshare where applicable, also include the license type, Apache as well where applicable.
- 12.) please compose a clean slate action plan outlining the steps above. we will execute each step independently, not all at once. by incrementaly changing the repo, I can watch for any errors that may occur, and take corrective action to resolve any issue.
- 12.a) if I missed any critical step in this doc, pertaining to the clean slate release prep, please add it to the action plan for review, titled observations and improvements.
- 12.b once the action plan has been fully realized and executed, I will push the repo, and tag it 1.0.0 for public use.

### End of "Clean Slate Release Plan"
