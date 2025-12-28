import logging
import google.generativeai as genai
import openai
from jinja2 import Environment, FileSystemLoader
import os
import json
from datetime import datetime
from pathlib import Path

from config import settings

logger = logging.getLogger(__name__)

# Jinja2 environment for templates
template_dir = os.path.join(os.path.dirname(__file__), '..', 'prompts')
jinja_env = Environment(loader=FileSystemLoader(template_dir))

# Initialize Google Generative AI
if settings.GOOGLE_API_KEY:
    genai.configure(api_key=settings.GOOGLE_API_KEY)

# Initialize OpenAI
if settings.OPENAI_API_KEY:
    openai.api_key = settings.OPENAI_API_KEY

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

    @celery_app.task(bind=True, name='tasks.generate_idea_gemini')
    def generate_idea_gemini(self, reference_keywords: str, reference_posts: list = None):
        """
        Generate an idea for a post based on reference keywords using Gemini.
        """
        try:
            self.update_state(state='PROGRESS', meta={'current': 'Rendering idea prompt'})

            template = jinja_env.get_template('idea_template.jinja2')
            prompt = template.render(
                reference_keywords=reference_keywords,
                reference_posts=reference_posts or []
            )

            self.update_state(state='PROGRESS', meta={'current': 'Calling Gemini API'})

            model = genai.GenerativeModel(settings.GOOGLE_MODEL)
            response = model.generate_content(prompt)
            idea = response.text

            logger.info(f"Successfully generated idea with Gemini for keywords: {reference_keywords}")

            idea_data = {
                'timestamp': datetime.now().isoformat(),
                'type': 'idea',
                'provider': 'gemini',
                'reference_keywords': reference_keywords,
                'reference_posts': reference_posts or [],
                'idea': idea
            }
            db_file = save_to_db(idea_data)

            generate_post_gemini.delay(
                idea=idea,
                reference_keywords=reference_keywords,
                reference_posts=reference_posts or [],
                db_file=db_file
            )

            return {'status': 'success', 'idea': idea, 'db_file': db_file}

        except Exception as e:
            logger.error(f"Error generating idea with Gemini: {str(e)}")
            return {'status': 'error', 'error': str(e)}

    @celery_app.task(bind=True, name='tasks.generate_post_gemini')
    def generate_post_gemini(self, idea: str, reference_keywords: str, reference_posts: list = None, db_file: str = None):
        """
        Generate a post based on the idea using Gemini.
        """
        try:
            self.update_state(state='PROGRESS', meta={'current': 'Rendering post prompt'})

            template = jinja_env.get_template('post_template.jinja2')
            prompt = template.render(
                idea=idea,
                reference_keywords=reference_keywords,
                reference_posts=reference_posts or []
            )

            self.update_state(state='PROGRESS', meta={'current': 'Calling Gemini API'})

            model = genai.GenerativeModel(settings.GOOGLE_MODEL)
            response = model.generate_content(prompt)
            post = response.text

            logger.info(f"Successfully generated post with Gemini for idea: {idea[:50]}...")

            if db_file and os.path.exists(db_file):
                with open(db_file, 'r') as f:
                    data = json.load(f)
                data['post'] = post
                data['post_generated_at'] = datetime.now().isoformat()
                with open(db_file, 'w') as f:
                    json.dump(data, f, indent=2)
                logger.info(f"Post added to {db_file}")
            else:
                post_data = {
                    'timestamp': datetime.now().isoformat(),
                    'type': 'post',
                    'provider': 'gemini',
                    'reference_keywords': reference_keywords,
                    'reference_posts': reference_posts or [],
                    'idea': idea,
                    'post': post
                }
                db_file = save_to_db(post_data)

            return {'status': 'success', 'post': post, 'db_file': db_file}

        except Exception as e:
            logger.error(f"Error generating post with Gemini: {str(e)}")
            return {'status': 'error', 'error': str(e)}

    @celery_app.task(bind=True, name='tasks.generate_idea_gpt')
    def generate_idea_gpt(self, reference_keywords: str, reference_posts: list = None):
        """
        Generate an idea for a post based on reference keywords using GPT.
        """
        try:
            self.update_state(state='PROGRESS', meta={'current': 'Rendering idea prompt'})

            template = jinja_env.get_template('idea_template.jinja2')
            prompt = template.render(
                reference_keywords=reference_keywords,
                reference_posts=reference_posts or []
            )

            self.update_state(state='PROGRESS', meta={'current': 'Calling OpenAI API'})

            response = openai.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}]
            )
            idea = response.choices[0].message.content

            logger.info(f"Successfully generated idea with GPT for keywords: {reference_keywords}")

            idea_data = {
                'timestamp': datetime.now().isoformat(),
                'type': 'idea',
                'provider': 'gpt',
                'reference_keywords': reference_keywords,
                'reference_posts': reference_posts or [],
                'idea': idea
            }
            db_file = save_to_db(idea_data)

            generate_post_gpt.delay(
                idea=idea,
                reference_keywords=reference_keywords,
                reference_posts=reference_posts or [],
                db_file=db_file
            )

            return {'status': 'success', 'idea': idea, 'db_file': db_file}

        except Exception as e:
            logger.error(f"Error generating idea with GPT: {str(e)}")
            return {'status': 'error', 'error': str(e)}

    @celery_app.task(bind=True, name='tasks.generate_post_gpt')
    def generate_post_gpt(self, idea: str, reference_keywords: str, reference_posts: list = None, db_file: str = None):
        """
        Generate a post based on the idea using GPT.
        """
        try:
            self.update_state(state='PROGRESS', meta={'current': 'Rendering post prompt'})

            template = jinja_env.get_template('post_template.jinja2')
            prompt = template.render(
                idea=idea,
                reference_keywords=reference_keywords,
                reference_posts=reference_posts or []
            )

            self.update_state(state='PROGRESS', meta={'current': 'Calling OpenAI API'})

            response = openai.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}]
            )
            post = response.choices[0].message.content

            logger.info(f"Successfully generated post with GPT for idea: {idea[:50]}...")

            if db_file and os.path.exists(db_file):
                with open(db_file, 'r') as f:
                    data = json.load(f)
                data['post'] = post
                data['post_generated_at'] = datetime.now().isoformat()
                with open(db_file, 'w') as f:
                    json.dump(data, f, indent=2)
                logger.info(f"Post added to {db_file}")
            else:
                post_data = {
                    'timestamp': datetime.now().isoformat(),
                    'type': 'post',
                    'provider': 'gpt',
                    'reference_keywords': reference_keywords,
                    'reference_posts': reference_posts or [],
                    'idea': idea,
                    'post': post
                }
                db_file = save_to_db(post_data)

            return {'status': 'success', 'post': post, 'db_file': db_file}

        except Exception as e:
            logger.error(f"Error generating post with GPT: {str(e)}")
            return {'status': 'error', 'error': str(e)}
