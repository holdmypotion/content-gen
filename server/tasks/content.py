import logging
import google.generativeai as genai
from jinja2 import Environment, FileSystemLoader
import os
import json
from datetime import datetime
from pathlib import Path

from config import settings

logger = logging.getLogger(__name__)

# p Jinja2 environment for templates
template_dir = os.path.join(os.path.dirname(__file__), '..', 'prompts')
jinja_env = Environment(loader=FileSystemLoader(template_dir))

# Initialize Google Generative AI
if settings.GOOGLE_API_KEY:
    genai.configure(api_key=settings.GOOGLE_API_KEY)

# Setup database directory for JSON storage
db_dir = os.path.join(os.path.dirname(__file__), '..', 'db')
Path(db_dir).mkdir(parents=True, exist_ok=True)


def save_to_db(data: dict) -> str:
    """Save data to timestamped JSON file in db directory."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
    filename = f"content_{timestamp}.json"
    filepath = os.path.join(db_dir, filename)

    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

    logger.info(f"Data saved to {filepath}")
    return filepath


def register_tasks(celery_app):
    """Register Celery tasks with the app instance."""

    @celery_app.task(bind=True, name='tasks.generate_idea')
    def generate_idea(self, reference_keywords: str, reference_posts: list = None):
        """
        Generate an idea for a post based on reference keywords.
        """
        try:
            self.update_state(state='PROGRESS', meta={'current': 'Rendering idea prompt'})

            # Load and render prompt template
            template = jinja_env.get_template('idea_template.jinja2')
            prompt = template.render(
                    reference_keywords=reference_keywords,
                    reference_posts=reference_posts or []
                    )

            self.update_state(state='PROGRESS', meta={'current': 'Calling Gemini API'})

            # Call Gemini API
            model = genai.GenerativeModel(settings.GOOGLE_MODEL)
            response = model.generate_content(prompt)

            idea = response.text

            logger.info(f"Successfully generated idea for keywords: {reference_keywords}")

            # Save idea to database
            idea_data = {
                    'timestamp': datetime.now().isoformat(),
                    'type': 'idea',
                    'reference_keywords': reference_keywords,
                    'reference_posts': reference_posts or [],
                    'idea': idea
                    }
            db_file = save_to_db(idea_data)

            # Enqueue post generation task
            generate_post.delay(
                    idea=idea,
                    reference_keywords=reference_keywords,
                    reference_posts=reference_posts or [],
                    db_file=db_file
                    )

            return {
                    'status': 'success',
                    'idea': idea,
                    'reference_keywords': reference_keywords,
                    'db_file': db_file
                    }

        except Exception as e:
            logger.error(f"Error generating idea: {str(e)}")
            return {
                    'status': 'error',
                    'error': str(e),
                    'reference_keywords': reference_keywords
                    }

    @celery_app.task(bind=True, name='tasks.generate_post')
    def generate_post(self, idea: str, reference_keywords: str, reference_posts: list = None, db_file: str = None):
        """
        Generate a post based on the idea.
        """
        try:
            self.update_state(state='PROGRESS', meta={'current': 'Rendering post prompt'})

            # Load and render prompt template
            template = jinja_env.get_template('post_template.jinja2')
            prompt = template.render(
                    idea=idea,
                    reference_keywords=reference_keywords,
                    reference_posts=reference_posts or []
                    )

            self.update_state(state='PROGRESS', meta={'current': 'Calling Gemini API'})

            # Call Gemini API
            model = genai.GenerativeModel(settings.GOOGLE_MODEL)
            response = model.generate_content(prompt)

            post = response.text

            logger.info(f"Successfully generated post for idea: {idea[:50]}...")

            # Save or update post data in database
            if db_file and os.path.exists(db_file):
                # Update existing file with post data
                with open(db_file, 'r') as f:
                    data = json.load(f)
                data['post'] = post
                data['post_generated_at'] = datetime.now().isoformat()
                with open(db_file, 'w') as f:
                    json.dump(data, f, indent=2)
                logger.info(f"Post added to {db_file}")
            else:
                # Create new file with both idea and post
                post_data = {
                        'timestamp': datetime.now().isoformat(),
                        'type': 'post',
                        'reference_keywords': reference_keywords,
                        'reference_posts': reference_posts or [],
                        'idea': idea,
                        'post': post
                        }
                db_file = save_to_db(post_data)

            return {
                    'status': 'success',
                    'post': post,
                    'idea': idea,
                    'reference_keywords': reference_keywords,
                    'db_file': db_file
                    }

        except Exception as e:
            logger.error(f"Error generating post: {str(e)}")
            return {
                    'status': 'error',
                    'error': str(e),
                    'idea': idea,
                    'reference_keywords': reference_keywords
                    }
