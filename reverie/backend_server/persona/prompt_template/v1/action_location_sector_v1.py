from utils import debug
from ..common import ActionLoc, openai_config
from ..gpt_structure import generate_prompt, safe_generate_structured_response
from ..print_prompt import print_run_prompts
import asyncio
# Variables:
# !<INPUT 0>! -- Persona name
# !<INPUT 1>! -- Maze all possible sectors
# !<INPUT 2>! -- Persona name
# !<INPUT 3>! -- Persona living sector
# !<INPUT 4>! -- Persona living sector arenas
# !<INPUT 5>! -- Persona name
# !<INPUT 6>! -- Persona current sector
# !<INPUT 7>! -- Persona current sector arenas
# !<INPUT 8>! -- curr action description
# !<INPUT 9>! -- Persona name

template = """
Task -- choose an appropriate area from the area options for a task at hand.

Sam Kim lives in {Sam Kim's house} that has Sam Kim's room, bathroom, kitchen.
Sam Kim is currently in {Sam Kim's house} that has Sam Kim's room, bathroom, kitchen.
Area options: {Sam Kim's house, The Rose and Crown Pub, Hobbs Cafe, Oak Hill College, Johnson Park, Harvey Oak Supply Store, The Willows Market and Pharmacy}.
* Stay in the current area if the activity can be done there. Only go out if the activity needs to take place in another place.
* Must be one of the "Area options," verbatim.
For taking a walk, Sam Kim should go to the following area: {Johnson Park}
---
Jane Anderson lives in {Oak Hill College Student Dormatory} that has Jane Anderson's room.
Jane Anderson is currently in {Oak Hill College} that has a classroom, library
Area options: {Oak Hill College Student Dormatory, The Rose and Crown Pub, Hobbs Cafe, Oak Hill College, Johnson Park, Harvey Oak Supply Store, The Willows Market and Pharmacy}.
* Stay in the current area if the activity can be done there. Only go out if the activity needs to take place in another place.
* Must be one of the "Area options," verbatim.
For eating dinner, Jane Anderson should go to the following area: {Hobbs Cafe}
---
!<INPUT 0>! lives in {!<INPUT 1>!} that has !<INPUT 2>!.
!<INPUT 3>! is currently in {!<INPUT 4>!} that has !<INPUT 5>!. !<INPUT 6>!
Area options: {!<INPUT 7>!}.
* Stay in the current area if the activity can be done there. Only go out if the activity needs to take place in another place.
* Must be one of the "Area options," verbatim.
!<INPUT 8>! is !<INPUT 9>!. For !<INPUT 10>!, !<INPUT 11>! should go to the following area: {
"""


async def run_gpt_prompt_action_sector(
  action_description, persona, maze, test_input=None, verbose=False
):
  def create_prompt_input(action_description, persona, maze, test_input=None):
    act_world = f"{maze.access_tile(persona.scratch.curr_tile)['world']}"

    prompt_input = []

    prompt_input += [persona.scratch.get_str_name()]
    prompt_input += [persona.scratch.living_area.split(":")[1]]
    x = f"{act_world}:{persona.scratch.living_area.split(':')[1]}"
    prompt_input += [persona.s_mem.get_str_accessible_sector_arenas(x)]

    prompt_input += [persona.scratch.get_str_name()]
    prompt_input += [f"{maze.access_tile(persona.scratch.curr_tile)['sector']}"]
    x = f"{act_world}:{maze.access_tile(persona.scratch.curr_tile)['sector']}"
    prompt_input += [persona.s_mem.get_str_accessible_sector_arenas(x)]

    if persona.scratch.get_str_daily_plan_req() != "":
      prompt_input += [f"\n{persona.scratch.get_str_daily_plan_req()}"]
    else:
      prompt_input += [""]

    # MAR 11 TEMP
    accessible_sector_str = persona.s_mem.get_str_accessible_sectors(act_world)
    curr = accessible_sector_str.split(", ")
    fin_accessible_sectors = []
    for i in curr:
      if "'s house" in i:
        if persona.scratch.last_name in i:
          fin_accessible_sectors += [i]
      else:
        fin_accessible_sectors += [i]
    accessible_sector_str = ", ".join(fin_accessible_sectors)
    # END MAR 11 TEMP

    prompt_input += [accessible_sector_str]

    action_description_1 = action_description
    action_description_2 = action_description
    if "(" in action_description:
      action_description_1 = action_description.split("(")[0].strip()
      action_description_2 = action_description.split("(")[-1][:-1]
    prompt_input += [persona.scratch.get_str_name()]
    prompt_input += [action_description_1]

    prompt_input += [action_description_2]
    prompt_input += [persona.scratch.get_str_name()]
    return prompt_input

  def __func_clean_up(gpt_response: ActionLoc, prompt=""):
    return gpt_response.area

  def __func_validate(gpt_response, prompt=""):
    sector = __func_clean_up(gpt_response)
    if len(sector.strip()) < 1:
      return False
    if "}" in sector:
      return False
    if "," in sector:
      return False
    return True

  def get_fail_safe():
    fs = "main room"
    return fs

  # # ChatGPT Plugin ===========================================================
  # def __chat_func_clean_up(gpt_response, prompt=""): ############
  #   cr = gpt_response.strip()
  #   return cr

  # def __chat_func_validate(gpt_response, prompt=""): ############
  #   try:
  #     gpt_response = __func_clean_up(gpt_response, prompt="")
  #   except:
  #     return False
  #   return True

  # print ("asdhfapsh8p9hfaiafdsi;ldfj as DEBUG 20") ########
  # gpt_param = {"engine": openai_config["model"], "max_tokens": 15,
  #              "temperature": 0, "top_p": 1, "stream": False,
  #              "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
  # prompt_template = "persona/prompt_template/v3_ChatGPT/action_location_sector_v2.txt" ########
  # prompt_input = create_prompt_input(action_description, persona, maze)  ########
  # prompt = generate_prompt(prompt_input, prompt_template)
  # example_output = "Johnson Park" ########
  # special_instruction = "The value for the output must contain one of the area options above verbatim (including lower/upper case)." ########
  # fail_safe = get_fail_safe() ########
  # output = ChatGPT_safe_generate_response(prompt, example_output, special_instruction, 3, fail_safe,
  #                                         __chat_func_validate, __chat_func_clean_up, True)
  # if output != False:
  #   return output, [output, prompt, gpt_param, prompt_input, fail_safe]
  # # ChatGPT Plugin ===========================================================

  gpt_param = {
    "engine": openai_config["model"],
    "max_tokens": 100,
    "temperature": 0,
    "top_p": 1,
    "stream": False,
    "frequency_penalty": 0,
    "presence_penalty": 0,
    "stop": None,
  }
  prompt_template = "persona/prompt_template/v1/action_location_sector_v1.py"
  prompt_input = create_prompt_input(action_description, persona, maze)
  prompt = generate_prompt(prompt_input, prompt_template_str=template)
  fail_safe = get_fail_safe()
  output = await safe_generate_structured_response(
    prompt,
    gpt_param,
    ActionLoc,
    5,
    fail_safe,
    __func_validate,
    __func_clean_up,
  )
  y = f"{maze.access_tile(persona.scratch.curr_tile)['world']}"
  x = [i.strip() for i in persona.s_mem.get_str_accessible_sectors(y).split(",")]
  if output not in x:
    # output = random.choice(x)
    output = persona.scratch.living_area.split(":")[1]

  # print ("DEBUG", random.choice(x), "------", output)

  if debug or verbose:
    print_run_prompts(prompt_template, persona, gpt_param, prompt_input, prompt, output)

  return output, [output, prompt, gpt_param, prompt_input, fail_safe]
