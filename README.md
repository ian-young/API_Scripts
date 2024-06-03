# API_Scripts

This is a private repository where API scripts and projects may live before being published to a different repository. Scripts that are ready to be published are found within the `main` branch. These scripts may be shared as long as they are located on the `main` branch since the credentials are not hard-coded. When sharing scripts, it is important to rememeber to send over the [requirements.txt](/requirements.txt) file and the [.env-generic](/.env-generic) file to give the user a base to work from. For more detailed information, please visit this repository's [Wiki](https://github.com/ian-young/API_Scripts/blob/main/Wiki/Home.md)

>[!IMPORTANT]
>When sending the `.env-generic` file over, it is important to remember to mentino that the name needs to be changed to `.env` and the file must be in the same directory as the script for the code to function properly.

The purpose of these scripts is:

* Enhance personal understanding of how to work with API
* Learn best practices when working with API
* Stay up to date with coding skills
  * Continue to learn how to optimize code
  * Experiment with new methods of running code and making calls
* Create automations that may be shared with customers or used on customer orgs

## Navigating the Repository

This repository has three branches:

1. The [`main`](https://github.com/ian-young/API_Scripts) branch which is where working, production-level code is located.
2. The [`wip`](https://github.com/ian-young/API_Scripts/tree/wip) branch is intended for code that is working but still has features that need to be developed or is in the debugging phase.
3. The [`ideas`](https://github.com/ian-young/API_Scripts/tree/ideas) branch is for any experimental code; this will see a higher volume of commits and not all of the code located here will be working.

>[!TIP]
>The order of development should start at the lowest branch, `ideas` and work its way up to the prodcution branch, `main`.

### Projects

Scripts that will have a larger impact will have an associated project where issues may be posted and organized for organized development of the script. Items that may be found in project can range from bug reports, documentation requests, feature requests, etc.

Current running projects in the repository are:

1. [Delete Devices](https://github.com/users/ian-young/projects/3)
   * This project is to aid with running VCE
   * Finished with phase 1
   * Beginning phase 2 soon
      * Need to find endpoints to list Guest sites, Desk Stations, Guest iPads, and Guest Printers.
      * Phase 2 is the finaly phase for this script and is expected to take longer
