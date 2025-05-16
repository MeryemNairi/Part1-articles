import os
import base64
from dotenv import load_dotenv
import google.generativeai as genai # type: ignore
import fal_client # type: ignore
from PIL import Image
from io import BytesIO

# Load environment variables
load_dotenv()

# Set up Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set in .env")
genai.configure(api_key=GEMINI_API_KEY)
gemini = genai.GenerativeModel('gemini-2.0-flash')

# Set up fal.ai
FAL_API_KEY = os.getenv("FAL_KEY")
if not FAL_API_KEY:
    raise ValueError("FAL_API_KEY is not set in .env")

def get_image_prompt_from_gemini(topic):
    system_prompt = (
        "You are a senior AI prompt engineer specializing in generative image models used for professional website design.\n\n"
        "Your task is to receive a general topic, interpret it intelligently, and generate a **ready-to-use prompt** "
        "for a photorealistic image that fits well as a **visual element for a website** (e.g. header, hero section, banner, blog article).\n\n"

        "Rules for interpreting the topic and generating the image prompt:\n"
        "1. First, analyze the topic and deduce its most suitable visual representation (you may infer the context: abstract, editorial, business, lifestyle, nature, technology, etc.).\n"
        "2. Then, write a full image prompt that is clear, visual, highly descriptive, and usable directly with AI image generation tools (such as Fal AI / Flux).\n\n"

        "Guidelines for the prompt:\n"
        "- Must describe a **visually appealing, 4K ultra-realistic scene** with depth, texture, and clarity.\n"
        "- The image must be **web design-friendly**, usable for modern websites (clean layout, balanced composition).\n"
        "- Avoid including any human faces, text, logos, flags, or religious symbols.\n"
        "- Use visual storytelling: you may include natural elements, objects, abstract compositions, modern buildings, or environments depending on the topic.\n"
        "- Add context when relevant: lighting (e.g. soft, cinematic), style (e.g. editorial, modern, minimal), perspective (e.g. wide angle, drone shot), and ambiance (e.g. calm, energetic).\n"
        "- Always keep the image composition **usable as a background or main visual** on a website. Prioritize clarity, focus, and balanced framing.\n\n"
        "- Do NOT explain, label, or wrap it in quotation marks."
        "-Absolutely do NOT include any description that refers to text, signs, letters, characters, or any form of writing — even decorative or calligraphic. "
        "-Assume the image will be used in a web context where all text is added separately via code."
        "- Include a coherent and modern color palette that enhances the website's visual identity (e.g. earthy tones, soft pastels, monochrome, vivid contrasts) depending on the topic.\n"
        "Your final output must include ONLY the generated prompt. Do not explain your reasoning, just return the image prompt, ready for use."
    )

    user_prompt = f"Topic: {topic}\n\nNow follow the steps above and provide the image prompt based on the topic given."
    
    response = gemini.generate_content([system_prompt, user_prompt])
    return response.text.strip()


def generate_image_with_fal(prompt, output_file):
    negative_prompt = (
        "person, human, face, people, portrait, profile, figure, "
        "text, writing, lettering, words, characters, sign, slogan, label, handwriting, numbers, "
        "religious symbol, flag, logo, watermark"
    )
    print(f"Generating image for prompt: {prompt}")
    result = fal_client.subscribe(
        "fal-ai/flux/schnell",
        arguments={
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "image_size": {"width": 1920, "height": 1080},
            "num_inference_steps": 8,
            "num_images": 1,
            "true_cfg": 9.0,
            "guidance_scale": 1.5,
            "quality": "premium",
            "sync_mode": True,
            "enable_safety_checker": True,
        },
        with_logs=True,
    )
    image_url = result['images'][0]['url']
    if 'base64,' in image_url:
        base64_data = image_url.split('base64,')[1]
        image_bytes = base64.b64decode(base64_data)
        img = Image.open(BytesIO(image_bytes))
        img.save(output_file)
        print(f"Image saved to {output_file}")
    else:
        print("Unexpected image URL format:", image_url)

def get_logo_prompt_from_gemini(topic):
    system_prompt = (
        "You are a senior AI prompt engineer and visual branding expert specializing in professional logo design for websites using WordPress.\n\n"
        "Your role is to generate a clean, modern, and high-quality logo **prompt** to be used by an AI image generation model (such as Fal AI Flux) based on a given topic.\n\n"

        "Instructions:\n"
        "1. Briefly interpret the topic and identify the most relevant symbolic visual elements.\n"
        "2. Then, generate a **detailed and actionable prompt** for the logo generator, following all the design rules below.\n\n"

        "Design Rules for the LOGO prompt:\n"
        "- The logo must be in **flat design or vector style**, with a **transparent background**.\n"
        "- Focus on **geometric, abstract, or symbolic elements** — not literal illustrations.\n"
        "- Do NOT include any text, letters, numbers, names, or typographic content + Absolutely NO text, slogan, year, number or writing in any part of the logo. No exceptions.\n"
        "- Avoid human faces, realistic animals, buildings, religious symbols, flags, or overly detailed visuals.\n"
        "- Use a **clean, modern color palette**, with a maximum of 2 to 3 colors. Suitable examples: tech blue, charcoal gray, mint green, off-white, or earth tones.\n"
        "- Avoid high-saturation or neon colors unless strictly required by the topic.\n"
        "- The logo must be **scalable**, usable from 64px to 1024px.\n"
        "- The logo must be perfectly centered in the image, with equal visual margin on all sides. Treat this as mandatory.\n"
        "- The composition must be **centered, balanced, and instantly recognizable**, even at small sizes.\n"
        "- Avoid any clutter, background textures, shadows, gradients, or unnecessary decoration.\n"
        "- The result must be perfectly suited for **WordPress usage**: clean in headers, adaptable to dark/light backgrounds, and usable as favicon.\n\n"
        "Output format:\n"
        "Return ONLY the final logo prompt, ready to be used with a generative image model like Fal AI Flux. Do NOT include context, explanations, or labels."
    )
    user_prompt = f"Topic: {topic}\nFirst, understand the context. Then, generate a robust logo prompt by following tha above instructions:"
    response = gemini.generate_content([system_prompt, user_prompt])
    return response.text.strip()

def generate_logo_with_fal(prompt, output_file):
    negative_prompt = (
        "text, words, letters, numbers, signature, watermark, low quality, blurry, human faces, realistic photos, clutter"
    )
    print(f"Generating logo for prompt: {prompt}")
    result = fal_client.subscribe(
        "fal-ai/flux/schnell",
        arguments={
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "image_size": {"width": 512, "height": 512},
            "num_inference_steps": 6,
            "num_images": 1,
            "true_cfg": 9.0,
            "guidance_scale": 2.0,
            "quality": "premium",
            "sync_mode": True,
            "enable_safety_checker": True,
        },
        with_logs=True,
    )
    image_url = result['images'][0]['url']
    if 'base64,' in image_url:
        base64_data = image_url.split('base64,')[1]
        image_bytes = base64.b64decode(base64_data)
        img = Image.open(BytesIO(image_bytes))
        img.save(output_file)
        print(f"Logo saved to {output_file}")
    else:
        print("Unexpected image URL format:", image_url)

 
if __name__ == "__main__":
    topic = "Digital Marketing in Morocco"
    # Generate photorealistic image
    prompt = get_image_prompt_from_gemini(topic)
    print("Gemini image prompt:", prompt)
    generate_image_with_fal(prompt, "output_image.png")
    # Generate logo
    logo_prompt = get_logo_prompt_from_gemini(topic)
    print("Gemini logo prompt:", logo_prompt)
    generate_logo_with_fal(logo_prompt, "output_logo.png")



    