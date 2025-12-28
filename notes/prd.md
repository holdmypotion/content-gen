# User Flow
1. User initiates the flow by clicking generate button on the UI. There will also be a text input to add reference keywords.
2. This comes to the backend server which intiates a task to generate an "idea" for the post. This will be an API call to gemini llm model with a prompt that we'll build to generate ideas.
3. Post completion of this task we'll enqueue another one to generate the actual post based on the idea that was generated in the previous step.
4. There will be another UI that the user can open up to see the latest generated post and the corresponding idea.


# Prompt
- we'll use jinja2 templating to build the prompt
- there will be a template which will have reference posts and the corresponding ideas that reflect the reference posts.
- we'll have separte prompt for post gen and idea gen but they'll use the same template
