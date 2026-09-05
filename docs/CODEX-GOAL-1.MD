# Role 
Consider yourself as a Full Stack Architect Specialized in React, Python, AI, Async processing etc and Implement things with best of your knowledge and abilities

# Run Instructions 
1) Run this with Parallel Agents if needed.

2) If you need any decision, go with `YES` for now, but document those decisions at /Users/mahesh-kulkarni/projects/coding-monkey-labs-client-projects/cml-memoryhive/docs/DECISIONS-GOAL-1.MD

3) Do not wait for my approval, take your Judgement call 

# WebApp Changes 

1) In the library, we have numbers of Items on top with Favorites etc. This Section, the items should work as filters. If I click, the bottom list gets filtered out. 

2) When we filter or group of filters, lets introduce a pattern of showing the Pills with X Buttons, so if I click on X, the Filter is removed and at same time the Pill is removed too. Implement this pills as common compoent and lets use it in all filters. 

3) We need Pills etc everywhere we are doing the Filters. 

4) The Title of the Card is clicable..Better to Implement a Show Details Button. And provide that too. When user Hover on the Title, or this Button, it should highlight and show.

5) Delete Button should have a the Confirmation popup, allow user to decide if they want to continue or cancel. 

6) On Cards, the Favorite Button Not working.  Or. Atleast it does not show up when we click on it.  Validate and fix

7) Implement a way for users to tag, untag a item. Cards favorite/UnFavorite not working in Any view. Also implement a Confirmation Dialog here. 

8) Archieve, unArchive - Lets implement those options.  There is no easy way to Archive and unArchive. Again Implement Confirmation Dialogs. 

9) IN General, all Delete Operation should be supported with Confirmation Dialog. Validate and add. 

11) From Organize, click to a Tag and route user to the Library with filters applied. Tags should be a filter on the Library too. Introduce all tags to be clicable. 

12) Settings Should have a way to change password too. Edit password should be supported with Confirm dialogs. And if user change password, then force logoff user with message that password changed successfully.

13) Synced on Left Nav -> Should show the date when it synced. 

14) LocalStorage etc.. plan it well. Logoff, cleans all localstorage, so login/logoff experiance should be good and crisp. 

15) Implement User Idle scenario and refresh the view after every 1 min, if screen is idle.  If Screen remains idle for 10+ mins, then logoff user with a message. 

16) Logoff Button not clearly visible. Better to implement a Button visible.. 

# Mobile App Changes

1) Mobile Features should be similar to the WebApp. Review all Features and Implement the ones which are missing. Also refer to the suggestions I gave for webapp. 

2) Item Details should be similar to the WebApp. 

3) In Capture or Edit, the Tags needs to be AutoSelect based on Search. When user selects a Tag, it shows up as Pill with X button, so that user get chance to Add / edit more tags etc 

4) Settings should align to the WebApp too 

5) Library and Search need to get better and aligned with WebApp, searching is key.. 

6) Organize Feature from WebApp is missing in webApp

7) We need our Mobile App, to be implemented for Android and IOS too.  Check readyness, and tell us what needs to be done. 

8) Validate Build for the Mobile App. Write the MD files on how to Build and test the Android and IOS Apps.

9) Does our Mobile App ready to publish on AppStore, Write a MD File talking about readyness and GAPs.. 

10) Generate all docs etc needed to publish apps to AppStore.. whats missing. 


# WebApp as Admin Persona 

1) We do not have a view for Admin Users. E.g. If I am a admin who is managing this app and all users etc.  I should have a admin level view of everyting. 

2) Implement Personas in the system, Admin, User for now.  

3) Admin User needs a lot of dashboards, and graphs etc. Think about all possible usecases Admin needs to know about and implement thoe workflows. Make sure to document it

4) As a Admin user, I should have a way to enable/disable access for Users in system. Also I should be able to delete the Users from and all their data etc. 

5) Admins manage this system so think about it overall.


# Temporal Pipelines App for offline Data Processing 

1) We need to identify usecases which can run in background for user actions.  Design a new docker and Temporal based app to support these operations. Lets define this in Python typiclaly, so all tasks would be implemented in python code 

2) We need a way, to Pick the Items from user Libraries and Peform analyssi and 
    2.1) For URLs, Generate the AI Analsis of those Items. 
    2.2) For Images, Run the OCR on it and generate the summary
    2.3) For Text, Run AI Analysis and prepare the content summary  

3) Add the column etc in Item DB, to maintain data about if Items is analyzed or not. Updating of this would happen offline and Temporal app tasks would update it. 

4) Think what else this app can do overall. 

# DB and Data Seeing

2) Implement Data Seeding Mechanism to validate these all things 

3) Implement Scripts to Start, Stop, Clean DB, Load DB with Mock Data etc.. 

4) IMplement Database backup mechanism.  Admin should have a view and a way to backup whole DB 


## Testing 

1) Test each of these apps to make sure they work in realtime on my docker containers 

2) Test WebApp, and Mobile App Both.  Check if we want to implement PlayWrite based Automation to Test UI workflows. Implement this as a Separate App under the project. 

3) Implement Scripts in the App, to 
   3.1) Run things on Docker Container 
   3.2) Validtae if things are running
   3.3) Use the Scripting to Load Data, Cleanup Data
   3.4) Automation should load mock data, validate high level scenarios and then tear down when closing 

4) Improvise wheverever you can. 


# Kubernetes Based Deployments 

1) Implement Build Pipeline, as suggested in the template /Users/mahesh-kulkarni/projects/coding-monkey-labs-client-projects/cml-zestro/docs/templates/BUILD_PIPELINE_BLUEPRINT.md

2) Implement the K8S Build and Deploy Pipeline as suggested in the Template /Users/mahesh-kulkarni/projects/coding-monkey-labs-client-projects/cml-zestro/docs/templates/K8S_DEPLOYMENT_BLUEPRINT.md

# KBS
1) Generate Agents.md and wiring for the Claude, Codex, Antigravity to start using Knowledge.md before making any changes
2) Generate Knowledge.MD Files in every Sub-Project and wire it with the Harness from Step 1
3) Implement Scripts to update/re-generate Knowledge.md when run 


