"""
Author: Joon Sung Park (joonspk@stanford.edu)

File: gpt_structure.py
Description: Wrapper functions for calling OpenAI APIs.
"""
import asyncio
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
import os
from utils import openai_api_key, use_openai, api_model
import json
import time
import traceback
import asyncio
from openai import AzureOpenAI, OpenAI, AsyncOpenAI
from openai_cost_logger import DEFAULT_LOG_PATH
from persona.prompt_template.openai_logger_singleton import OpenAICostLogger_Singleton
# Fix config path to be relative to current file location
config_path = Path(__file__).parent.parent.parent.parent.parent / "openai_config.json"
with open(config_path, "r") as f:
  openai_config = json.load(f) 
#client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

if not use_openai:
  # TODO: The 'openai.api_base' option isn't read in the client API. You will need to pass it when you instantiate the client, e.g. 'OpenAI(base_url=api_base)'
  # openai.api_base = api_base
  model = api_model

# from langchain.llms import Ollama
# from langchain.llms import OpenAI
# from langchain.llms import LlamaCpp
# from langchain.llms import GPT4All
# from langchain.chat_models import ChatAnthropic
# from langchain.embeddings import GPT4AllEmbeddings
# from langchain.callbacks.manager import CallbackManager
# from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
# from langchain.llms import HuggingFacePipeline


# ============================================================================
# ################### [Set LLM] ###################
# ============================================================================



# def llm(prompt):
#   log = open("log.txt", "a")
#   log.write(f"Prompt @ {time.time()}: {prompt}\n")
#   api_url = "http://<instance-ip>:8000/generate"

#   payload = {
#       "inputs": [{"role": "user", "content": prompt}], 
#       "parameters": {"max_new_tokens": 25, "top_p": 0.9, "temperature": 0.6, "do_sample": True}
#   }
#   headers = {'Content-Type': 'application/json'}
#   response = requests.post(api_url, data=json.dumps(payload), headers=headers)
#   response = response.json()
#   log.write(f"Response @ {time.time()}: {response}\n")
#   log.close()

#   return response['text']

def setup_client(type: str, config: dict):
  """Setup the OpenAI client.

  Args:
      type (str): the type of client. Either "azure" or "openai".
      config (dict): the configuration for the client.

  Raises:
      ValueError: if the client is invalid.

  Returns:
      The client object created, either AzureOpenAI or OpenAI.
  """
  if type == "azure":
    client = AzureOpenAI(
      azure_endpoint=config["endpoint"],
      api_key=config["key"],
      api_version=config["api-version"],
    )
  elif type == "openai":
    client = AsyncOpenAI(
      api_key=config["key"],
    )
  else:
    raise ValueError("Invalid client")
  return client

if openai_config["client"] == "azure":
  client = setup_client("azure", {
    "endpoint": openai_config["model-endpoint"],
    "key": openai_config["model-key"],
    "api-version": openai_config["model-api-version"],
  })
elif openai_config["client"] == "openai":
  client = setup_client("openai", { "key": openai_config["model-key"] })
  client.base_url = "https://openrouter.ai/api/v1"
if openai_config["embeddings-client"] == "azure":  
  embeddings_client = setup_client("azure", {
    "endpoint": openai_config["embeddings-endpoint"],
    "key": openai_config["embeddings-key"],
    "api-version": openai_config["embeddings-api-version"],
  })
elif openai_config["embeddings-client"] == "openai":
  embeddings_client = setup_client("openai", { "key": openai_config["embeddings-key"] })
else:
  raise ValueError("Invalid embeddings client")

cost_logger = OpenAICostLogger_Singleton(
  experiment_name = openai_config["experiment-name"],
  log_folder = DEFAULT_LOG_PATH,
  cost_upperbound = openai_config["cost-upperbound"]
)


def temp_sleep(seconds=0.1):
  time.sleep(seconds)


async def ChatGPT_single_request(prompt):
  await temp_sleep()

  print("--- ChatGPT_single_request() ---")
  print("Prompt:", prompt)

  completion = await client.chat.completions.create(
    model=openai_config["model"],
    messages=[{"role": "user", "content": prompt}],
  )

  content = completion.choices[0].message.content
  print("Response content:", content)

  if content:
    content = content.strip("`").removeprefix("json").strip()
    return content
  else:
    print("ERROR: No message content from LLM.")
    return ""

async def ChatGPT_request(prompt):
  """
  Given a prompt and a dictionary of GPT parameters, make a request to OpenAI
  server and returns the response. 
  ARGS:
    prompt: a str prompt
    gpt_parameter: a python dictionary with the keys indicating the names of  
                   the parameter and the values indicating the parameter 
                   values.   
  RETURNS: 
    a str of GPT-3's response. 
  """
  # await temp_sleep()
  print("--- ChatGPT_request() ---")
  print("Prompt:", prompt)

  try: 
    completion = await client.chat.completions.create(
      model=openai_config["model"],
      messages=[{"role": "user", "content": prompt}]
    )
    content = completion.choices[0].message.content
    print("Response content:", content)
    cost_logger.update_cost(
      completion, input_cost=openai_config["model-costs"]["input"], output_cost=openai_config["model-costs"]["output"]
    )
    if content:
      content = content.strip("`").removeprefix("json").strip()
    return content
  
  except Exception as e: 
    print(f"Error: {e}")
    traceback.print_exc()
    return "LLM ERROR"

async def ChatGPT_structured_request(prompt, response_format):
  """
  Given a prompt and a dictionary of GPT parameters, make a request to OpenAI
  server and returns the response. 
  ARGS:
    prompt: a str prompt
    gpt_parameter: a python dictionary with the keys indicating the names of  
                   the parameter and the values indicating the parameter 
                   values.   
  RETURNS: 
    a str of GPT-3's response. 
  """
  print("--- ChatGPT_request() ---")
  print("Prompt:", prompt)

  try: 
    completion = await client.beta.chat.completions.parse(
      model=openai_config["model"],
      response_format=response_format,
      messages=[{"role": "user", "content": prompt}]
    )

    print("Response:", completion)
    message = completion.choices[0].message

    cost_logger.update_cost(
      completion,
      input_cost=openai_config["model-costs"]["input"],
      output_cost=openai_config["model-costs"]["output"],
    )

    if message.parsed:
      return message.parsed
    if message.refusal:
      raise ValueError("Request refused: " + message.refusal)
    raise ValueError("No parsed content or refusal found.")

  except Exception as e: 
    print(f"Error: {e}")
    traceback.print_exc()
    return "LLM ERROR"


# def GPT4_safe_generate_response(
#   prompt,
#   example_output,
#   special_instruction,
#   repeat=3,
#   fail_safe_response="error",
#   func_validate=None,
#   func_clean_up=None,
#   verbose=False,
# ):
#   if func_validate and func_clean_up:
#     prompt = 'GPT-3 Prompt:\n"""\n' + prompt + '\n"""\n'
#     prompt += (
#       f"Output the response to the prompt above in json. {special_instruction}\n"
#     )
#     prompt += "Example output json:\n"
#     prompt += '{"output": "' + str(example_output) + '"}'

#     if verbose:
#       print("CHAT GPT PROMPT")
#       print(prompt)

#     for i in range(repeat):
#       try:
#         gpt4_response = GPT4_request(prompt)
#         if not gpt4_response:
#           raise Exception("No valid response from GPT-4.")
#         curr_gpt_response = gpt4_response.strip()
#         end_index = curr_gpt_response.rfind("}") + 1
#         curr_gpt_response = curr_gpt_response[:end_index]
#         curr_gpt_response = json.loads(curr_gpt_response)["output"]

#         if func_validate(curr_gpt_response, prompt=prompt):
#           return func_clean_up(curr_gpt_response, prompt=prompt)

#         if verbose:
#           print("---- repeat count: \n", i, curr_gpt_response)
#           print(curr_gpt_response)
#           print("~~~~")

#       except Exception as e:
#         print("ERROR:", e)

#   return False


async def ChatGPT_safe_generate_response(
  prompt,
  example_output="",
  special_instruction="",
  repeat=3,
  fail_safe_response="error",
  func_validate=None,
  func_clean_up=None,
  verbose=False,
):
  if func_validate and func_clean_up:
    # prompt = 'GPT-3 Prompt:\n"""\n' + prompt + '\n"""\n'
    prompt = '"""\n' + prompt + '\n"""\n'
    if example_output or special_instruction:
      prompt += (
        f"Output the response to the prompt above in json. {special_instruction}\n"
      )
      if example_output:
        prompt += "Example output json:\n"
        prompt += '{"output": "' + str(example_output) + '"}'

    if verbose:
      print("LLM PROMPT")
      print(prompt)

    for i in range(repeat):
      try:
        chatgpt_response = await ChatGPT_request(prompt)
        if not chatgpt_response:
          raise Exception("Error: No valid response from LLM.")
        curr_gpt_response = chatgpt_response.strip()
        if example_output or special_instruction:
          end_index = curr_gpt_response.rfind("}") + 1
          curr_gpt_response = curr_gpt_response[:end_index]
          curr_gpt_response = json.loads(curr_gpt_response)["output"]

        if verbose:
          print("---- repeat count:", i)
          print("~~~~ curr_gpt_response:")
          print(curr_gpt_response)
          print("~~~~")

        if func_validate(curr_gpt_response, prompt=prompt):
          return func_clean_up(curr_gpt_response, prompt=prompt)

      except Exception as e:
        print("Error:", e)
        traceback.print_exc()

  print("Error: Fail safe triggered.")
  return fail_safe_response


async def ChatGPT_safe_generate_structured_response(
  prompt,
  response_format,
  example_output="",
  special_instruction="",
  repeat=3,
  fail_safe_response="error",
  func_validate=None,
  func_clean_up=None,
  verbose=False,
):
  if func_validate and func_clean_up:
    prompt = '"""\n' + prompt + '\n"""\n'
    if example_output or special_instruction:
      prompt += (
        f"Output the response to the prompt above in json. {special_instruction}\n"
      )
      if example_output:
        prompt += "Example output json:\n"
        prompt += str(example_output)

    if verbose:
      print("LLM PROMPT")
      print(prompt)

    for i in range(repeat):
      try:
        curr_gpt_response = await ChatGPT_structured_request(prompt, response_format)
        if not curr_gpt_response:
          raise ValueError("No valid response from LLM.")

        if verbose:
          print("---- repeat count:", i)
          print("~~~~ curr_gpt_response:")
          print(curr_gpt_response)
          print("~~~~")

        if (
          not isinstance(curr_gpt_response, str)
          and func_validate(curr_gpt_response, prompt=prompt)
        ):
          return func_clean_up(curr_gpt_response, prompt=prompt)
        else:
          print("Error: Response validation failed. Response:")
          print(curr_gpt_response)

      except Exception as e:
        print("Error:", e)
        traceback.print_exc()

  return fail_safe_response


# ============================================================================
# ###################[SECTION 2: ORIGINAL GPT-3 STRUCTURE] ###################
# ============================================================================
async def GPT_request(prompt, gpt_parameter):
  """
  Given a prompt and a dictionary of GPT parameters, make a request to OpenAI
  server and returns the response. 
  ARGS:
    prompt: a str prompt
    gpt_parameter: a python dictionary with the keys indicating the names of  
                   the parameter and the values indicating the parameter 
                   values.   
  RETURNS: 
    a str of GPT-3's response. 
  """
  temp_sleep()

  try:
    if use_openai:
      messages = [{
        "role": "system", "content": prompt
      }]
      response = await client.chat.completions.create(
                  model=gpt_parameter["engine"],
                  messages=messages,
                  temperature=gpt_parameter["temperature"],
                  max_tokens=gpt_parameter["max_tokens"],
                  top_p=gpt_parameter["top_p"],
                  frequency_penalty=gpt_parameter["frequency_penalty"],
                  presence_penalty=gpt_parameter["presence_penalty"],
                  stream=gpt_parameter["stream"],
                  stop=gpt_parameter["stop"],
              )
    else:
      response = await client.completions.create(model=model, prompt=prompt)

    print("Response: ", response)
    content = response.choices[0].message.content
    print("Content: ", content)
    return content

  except Exception as e:
    print("Error:", e)
    traceback.print_exc()
    return "REQUEST ERROR"


async def GPT_structured_request(prompt, gpt_parameter, response_format):
  """
  Given a prompt, a dictionary of GPT parameters, and a response format, make a request to OpenAI
  server and returns the response.
  ARGS:
    prompt: a str prompt
    gpt_parameter: a python dictionary with the keys indicating the names of
                   the parameter and the values indicating the parameter
                   values.
    response_format: a Pydantic model that defines the desired response format.
  RETURNS:
    a str of GPT-3's response.
  """
  temp_sleep()

  try:
    if use_openai:
      messages = [{
        "role": "system", "content": prompt
      }]
      response = await client.beta.chat.completions.parse(
        model=gpt_parameter["engine"],
        messages=messages,
        response_format=response_format,
        temperature=gpt_parameter["temperature"],
        max_tokens=gpt_parameter["max_tokens"],
        top_p=gpt_parameter["top_p"],
        frequency_penalty=gpt_parameter["frequency_penalty"],
        presence_penalty=gpt_parameter["presence_penalty"],
        # stream=gpt_parameter["stream"],
        stop=gpt_parameter["stop"],
      )
    else:
      response = await client.completions.create(model=model, prompt=prompt)

    print("Response: ", response)
    message = response.choices[0].message

    if message.parsed:
      return message.parsed
    if message.refusal:
      raise ValueError("Request refused: " + message.refusal)
    raise ValueError("No parsed content or refusal found.")
  except Exception as e:
    print("Error:", e)
    traceback.print_exc()
    return "REQUEST ERROR"


def generate_prompt(curr_input, prompt_lib_file='', prompt_template_str=''):
  """
  Takes in the current input (e.g. comment that you want to classifiy) and
  either the path to a prompt file or the prompt template string itself. The
  prompt file contains the raw str prompt that will be used, which contains the
  following substr: !<INPUT>! -- this function replaces this substr with the
  actual curr_input to produce the final promopt that will be sent to the GPT3
  server.

  ARGS:
    curr_input: the input we want to feed in (IF THERE ARE MORE THAN ONE
                INPUT, THIS CAN BE A LIST.)
    prompt_lib_file: the path to the promopt file.
    prompt_template_str: the prompt template string.
  RETURNS:
    a str prompt that will be sent to OpenAI's GPT server.
  """
  if type(curr_input) == type("string"):
    curr_input = [curr_input]
  curr_input = [str(i) for i in curr_input]

  if prompt_lib_file:
    with open(prompt_lib_file, "r") as f:
      prompt = f.read()
  elif prompt_template_str:
    prompt = prompt_template_str
  else:
    raise ValueError("Either prompt_lib_file or prompt_template_str must be provided.")

  for count, i in enumerate(curr_input):
    prompt = prompt.replace(f"!<INPUT {count}>!", i)
  if "<commentblockmarker>###</commentblockmarker>" in prompt:
    prompt = prompt.split("<commentblockmarker>###</commentblockmarker>")[1]
  return prompt.strip()


async def safe_generate_response(prompt, 
                           gpt_parameter,
                           repeat=5,
                           fail_safe_response="error",
                           func_validate=None,
                           func_clean_up=None,
                           verbose=False): 
  if verbose: 
    print (prompt)

  if func_validate and func_clean_up:
    for i in range(repeat):
      curr_gpt_response = await GPT_request(prompt, gpt_parameter)
      try:
        if func_validate(curr_gpt_response, prompt=prompt):
          return func_clean_up(curr_gpt_response, prompt=prompt)
        else:
          print("Error: Response validation failed. Response:")
          print(curr_gpt_response)
      except Exception as e:
        print("Could not process response. Error:", e)
        traceback.print_exc()
      if verbose:
        print("---- repeat count: ", i, curr_gpt_response)
        print(curr_gpt_response)
        print("~~~~")

  print("Error: Fail safe triggered.")
  return fail_safe_response


async def safe_generate_structured_response(    
  prompt,
  gpt_parameter,
  response_format,
  repeat=5,
  fail_safe_response="error",
  func_validate=None,
  func_clean_up=None,
  verbose=False
):
  if verbose:
    print(prompt)

  if func_validate and func_clean_up:
    for i in range(repeat):
      curr_gpt_response = await GPT_structured_request(prompt, gpt_parameter, response_format)
      try:
        if not isinstance(curr_gpt_response, str) and func_validate(
          curr_gpt_response,
          prompt=prompt
        ):
          return func_clean_up(curr_gpt_response, prompt=prompt)
        print("Error: Response validation failed. Response:")
        print(curr_gpt_response)
      except Exception as e:
        print("Could not process response. Error:", e)
        traceback.print_exc()
      if verbose:
        print("---- repeat count: ", i, curr_gpt_response)
        print(curr_gpt_response)
        print("~~~~")

  print("Error: Fail safe triggered.")
  return fail_safe_response


def get_embedding(text, model=openai_config["embeddings"]):
  text = text.replace("\n", " ")
  if not text: 
    text = "this is blank"
  response = embeddings_client.embeddings.create(input=[text], model=model)
  cost_logger.update_cost(response=response, input_cost=openai_config["embeddings-costs"]["input"], output_cost=openai_config["embeddings-costs"]["output"])
  return response.data[0].embedding

# def get_embedding(documents):
#   api_url = "http://<instance-ip>:8000/embed"
#   payload = {"documents": documents}
#   response = requests.post(api_url, json=payload)
#   response = response.json()
#   return response


if __name__ == '__main__':
  gpt_parameter = {"engine": openai_config["model"], "max_tokens": 100, 
                   "temperature": 0, "top_p": 1, "stream": False,
                   "frequency_penalty": 0, "presence_penalty": 0, 
                   "stop": ['\n']}
  curr_input = ["driving to a friend's house"]
  prompt_lib_file = Path(__file__).parent / "v1" / "unused" / "test_prompt_July5.txt"
  prompt = generate_prompt(curr_input, prompt_lib_file)

  def __func_validate(gpt_response,prompt=""): 
    if len(gpt_response.strip()) <= 1:
      return False
    if len(gpt_response.strip().split(" ")) > 1: 
      return False
    return True
  def __func_clean_up(gpt_response,prompt=""):
    cleaned_response = gpt_response.strip()
    return cleaned_response
  output = asyncio.run(safe_generate_response(prompt, 
                                 gpt_parameter,
                                 3,
                                 "rest",
                                 __func_validate,
                                 __func_clean_up,
                                 True))

  print(output)
