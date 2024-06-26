"""
This file includes text "templates", or functions that dynamically fill sentences given a passed amount of information. Includes functions that take key information and format it in a client-friendly string or RichText object that can be used in summary reports.
"""

import src.objects.agency as agency
import src.utility as utility
import src.output.dataframe.transformations as df_transformations
from src.output.text.processing.excel import get_richtext_from_variable
import src.output.text.processing.excel as excel
from src.constants import DEFAULT_FONT

from docxtpl import RichText
import numpy as np

def get_goal_change_summary_sentence(agency):
    """
    Given a passed agency, returns a sentence summarizing the change in total goal status across the agency from quarter to quarter.

    :param agency: An Agency object representing a CFO Act agency at a given point in time.
    :return: A string summarizing the quarter-over-quarter goal status change of the passed agency in the format "{number of occurrences} goals {goal status} last quarter to {number of occurrences} goals {goal status} this quarter."
    """
    previous_quarter, previous_year = utility.get_previous_quarter_and_year(agency.get_quarter(), agency.get_year())

    current_goal_statuses = agency.get_goal_status_df()["Status"]
    previous_goal_statuses = agency.get_goal_status_df(quarter=previous_quarter, year=previous_year)["Status"]
    
    to_return = ""
    
    # loops through each the previous and current goal status lists, accompanying string based on which list is being used
    for status_list, last_or_this_quarter in zip([previous_goal_statuses, current_goal_statuses], ["last quarter", "this quarter"]):
        status_strs = []    # list to hold each string uniquely describing goal status
    
        for status in status_list.unique():
            num_status = (status_list == status).sum()  # number of occurrences of given status
            plural_formatting = ("s" if num_status > 1 else "")
            status_strs.append(f"{num_status} goal{plural_formatting} {status.lower()}")

        to_return += f"{' and '.join(status_strs)} {last_or_this_quarter}"  # joins each string together with "and" keyword
        to_return += ' to ' if last_or_this_quarter == 'last quarter' else ''   # adds a connecting word if in the first loop
        
    return __process_template_output(to_return)

def get_goal_status_breakdown_bullets(agency):
    """
    Returns a RichText object representing the change in each goal status quarter-over-quarter, which is capable of being represented as a bulleted list. NOTE: The returned RichText object itself does not return a bulleted list, but each paragraph renders as a bullet when placed in a bulleted list in a template document.

    :param agency: An Agency object representing a CFO Act agency at a given point in time.
    :return: A RichText object describing the change in each agency goal quarter-over-quarter that is capable of being represented as a bulleted list.
    """
    rt = RichText()

    goals_list = agency.get_goals()

    # each loop creates a new paragraph for a unique agency goal
    for i in range(len(goals_list)):
        goal_name = goals_list[i]

        current_goal_status = agency.get_goal_status(goal_name)
        previous_goal_status = agency.get_goal_status(goal_name, quarter="previous")

        rt.add(str(goal_name), bold=True, font=DEFAULT_FONT)   # bolds the goal name at the beginning of the line
        rt.add(f"'s team identified the status of the goal as {current_goal_status.lower()} this quarter, ", font=DEFAULT_FONT)

        # the next section of the line is conditional based on whether the goal status has stayed the same, progressed or regressed
        if current_goal_status == previous_goal_status:
            rt.add(f"remaining consistent at its reported status of {previous_goal_status.lower()} last quarter.", font=DEFAULT_FONT)
        elif utility.goal_is_progressing(current_goal_status, previous_goal_status):
            rt.add(f"progressing from a status of {previous_goal_status.lower()} last quarter.", font=DEFAULT_FONT)
        else:   # goal is regressing
            rt.add(f"dropping from a status of {previous_goal_status.lower()} reported last quarter.", font=DEFAULT_FONT)
        
        if i != len(goals_list) - 1:
            rt.add("\a", font=DEFAULT_FONT)    # adds a paragraph break following each goal status statement (except for the final one)

    return __process_template_output(rt)

def get_challenge_summary_text(agency):
    """
    Returns a RichText object summarizing the challenges reported across the passed agency this quarter.

    :param agency: An Agency object representing a CFO Act agency at a given point in time.
    :return: A RichText object summarizing the passed agency's goal status in the quarter that it is reporting for.
    """
    rt = RichText()

    challenges_df = df_transformations.get_challenge_count_by_quarter(agency.get_agency_df())   # retrieve challenge count df
    challenges_df = challenges_df.loc[  # filter for agency year and quarter
        (challenges_df["Quarter"] == agency.get_quarter()) & 
        (challenges_df["Fiscal Year"] == agency.get_year()
    )]  

    # Retrieving most common challenges as a DataFrame
    most_common_challenges_df = challenges_df.loc[challenges_df["Count"] == challenges_df["Count"].max()]  # filter for only challenges with maximum count
    most_common_challenges_list = list(most_common_challenges_df["Challenge"])

    # Retrieving least common challenges as a DataFrame
    least_common_challenges_df = challenges_df.loc[challenges_df["Count"] == challenges_df["Count"].min()]  # filter for only challenges with minimum count
    least_common_challenges_list = list(least_common_challenges_df["Challenge"])

    challenges_dict = {
        "most common": most_common_challenges_list, 
        "least common": least_common_challenges_list 
    }

    for key, value in challenges_dict.items():
        challenge_list = value    # retrives the list (either most common or least common challenges) to be added to RichText in this loop

        for j in range(len(challenge_list)):
            challenge = challenge_list[j]

            # Operations for if there are more than one most common challenges
            if j != 0:
                rt.add(" and ", font=DEFAULT_FONT)  # adds connecting word for multiple challenges
                challenge = challenge.lower()   # keeps the first challenge in the list uppercase, all others lowercase

            rt.add(challenge, bold=True, font=DEFAULT_FONT) 

        if key == "most common":
            rt.add(" were the most commonly reported challenges across the agency's APG teams.", font=DEFAULT_FONT)
            rt.add("\n\n")    # line break in between most common and least common challenges
        else:
            rt.add(" were the least commonly reported challenges across the agency's APG teams.", font=DEFAULT_FONT)

    return __process_template_output(rt)

def get_speedometer_summary_text(agency, apg_name): 
    """
    Returns a RichText object describing the information conveyed in the speedometer figure displayed for the passed APG.

    :param agency: An Agency object representing a CFO Act agency at a given point in time.
    :param apg_name: The name of the APG whose status will be summarized.
    :return: A RichText object describing the information conveyed in the speedometer figure displayed for the passed APG.
    """
    # Obtaining the row that represents the APG in the reporting quarter/fiscal year
    apg_row = agency.get_apg_row(apg_name)

    # Retrieving information to be placed in strings, added to the RichText object
    status = apg_row["Status"].values[0].lower()

    placeholder_map = {
        "status": status, 
        "quarter": agency.get_quarter(), 
        "year": agency.get_year()
    }

    return __process_template_output(get_richtext_from_variable("speedometer_text", placeholder_map))

def get_blockers_text(agency, apg_name):
    """
    Returns a string describing the blockers identified for the passed agency and APG. String returned is raw input given in cover sheet.

    :param agency: An Agency object representing a CFO Act agency at a given point in time.
    :param apg_name: The name of the APG whose status will be summarized.
    :return: A string describing the blockers identified for the passed agency and APG. String returned is raw input given in cover sheet.
    """
    # Obtaining the row that represents the APG in the reporting quarter/fiscal year
    apg_row = agency.get_apg_row(apg_name)

    return __process_template_output(apg_row["Blockers"].values[0])

def get_group_help_text(agency, apg_name):
    """
    Returns a RichText object describing the help that the passed APG's goal team has requested from various sectors.

    :param agency: An Agency object representing a CFO Act agency at a given point in time.
    :param apg_name: The name of the APG whose status will be summarized.
    :return: A RichText object describing the help that the passed APG's goal team has requested from various sectors.
    """
    rt = RichText()

    apg_row = agency.get_apg_row(apg_name)

    apg_help_requested = apg_row.loc[:, apg_row.columns[apg_row.columns.str.contains("help")]]    # a DataFrame with only the columns indicating help requested

    for name, value in zip(apg_help_requested.columns, apg_help_requested.values[0]):
        # Adds field value to summary report if the field holds a string, i.e., if it was filled out in the cover sheet
        if isinstance(value, str):
            # Adds a line break if lines have already been created
            if rt.xml:
                rt.add("\n\n")
            
            header_text = name.replace(" help", "")     # creates header name from the column name via removing the "help" indicator of column

            rt.add(f"{header_text}:", bold=True, font=DEFAULT_FONT)
            rt.add(f" {value}", font=DEFAULT_FONT)

    return __process_template_output(rt)

def get_apg_challenges_bullets(agency, apg_name, tpl):
    """
    Returns a RichText object listing out the challenges reported by the APG goal team during the reported quarter, which is capable of being represented as a bulleted list. NOTE: The returned RichText object itself does not return a bulleted list, but each paragraph renders as a bullet when placed in a bulleted list in a template document.

    :param agency: An Agency object representing a CFO Act agency at a given point in time.
    :param apg_name: The name of the APG whose status will be summarized.
    :param tpl: An initialized DocxTemplate object. The object is required to create hyperlinks, but is not modified in any way within this function.
    :return: A RichText object object listing out the challenges reported by the APG goal team during the reported quarter, which is capable of being represented as a bulleted list. 
    """
    rt = RichText()

    challenges_list = agency.get_challenges(apg_name)

    # Add every challenge in list to RichText object
    for i in range(len(challenges_list)):
        challenge = challenges_list[i]

        rt.add(f"{challenge}", font=DEFAULT_FONT)

        recs = excel.get_recommendations_for_challenge(challenge)  # retrieves all recommendations for the given challenge
        
        if len(recs):
            rt.add(" — consider the following: ", font=DEFAULT_FONT)    # transition text
            
            for j in range(len(recs)):
                rec = recs[j]
                rt.add(f"{rec['Recommended Action']}", font=DEFAULT_FONT, url_id=tpl.build_url_id(rec["URL"]), color="#0000FF", underline=True) # adds recommended action with hyperlink

                if j != len(recs) - 1:
                    rt.add(", ", font=DEFAULT_FONT)     # adds commas to separate challenges

        if i != len(challenges_list) - 1:
            rt.add("\a")    # adds a paragraph break following each challenge (except for the final one)

    return __process_template_output(rt)

def get_success_story(agency, apg_name):
    """
    Returns the success story submitted for the quarter and fiscal year that the passed Agency object represents. 

    :param agency: An Agency object representing a CFO Act agency at a given point in time.
    :return: The success story from the quarter and year held by the passed Agency object.
    """
    apg_row = agency.get_apg_row(apg_name)

    return __process_template_output(apg_row["Success Story"].values[0])

def get_recurring_challenges_text(challenge_name, goal_name, count):
    """
    Returns a RichText object describing the passed recurring challenge.

    :param challenge_name: The name of the recurring challenge.
    :param goal_name: The name of the goal for which the challenge has been repeatedly reported.
    :param count: The number of consecutive quarters that the challenge has been reported for.
    :return: A RichText object describing the passed recurring challenge.
    """
    placeholders_dict = {
        "challenge": challenge_name,
        "goal": goal_name,
        "challenge count": count
    }

    return __process_template_output(get_richtext_from_variable("recurring_challenge_text", placeholders_dict))

def get_rec_text_block(rec, explanation, url):
    """
    Given a passed recommendation, explanation and URL, returns a RichText object representing a text block of the passed values.

    :param rec: The recommendation made based on a challenge that an agency is facing.
    :param explanation: The explanation offered on why the recommendation was made.
    :param url: The URL that provides more information about the recommendation.
    :return: A RichText object describing the recommendation and linking to a URL to learn more about the recommendation.
    """
    rt = RichText()

    rt.add("Consider ", bold=True, font=DEFAULT_FONT)
    rt.add(rec, font=DEFAULT_FONT, url_id=url, color="#0000FF", underline=True, bold=True) # adds recommended action with hyperlink
    rt.add(f": {__process_template_output(explanation)}", font=DEFAULT_FONT)    # processes explanation to catch NaN values

    return rt

def get_cap_goals_list(agency, goal_name):
    """
    Given the passed agency, returns all of the CAP goals that are related to it in a readable string.

    :param agency: An Agency object representing a CFO Act agency at a given point in time.
    :param goal_name: The name of the goal for which the challenge has been repeatedly reported.
    :return: A readable string respresenting the list of CAP goals associated with the passed agency.
    """
    cap_goals = agency.get_cap_goals(goal_name)

    return __list_to_str(cap_goals)

def get_outcomes_list(agency, goal_name):
    """
    Given the passed agency, returns a list of related outcomes in a readable string.

    :param agency: An Agency object representing a CFO Act agency at a given point in time.
    :param goal_name: The name of the goal for which the challenge has been repeatedly reported.
    :return: A readable string respresenting the list of outcomes associated with the passed agency.
    """
    outcomes = agency.get_outcomes(goal_name)

    return __list_to_str(outcomes)

def __list_to_str(input_list):
    """
    Converts the passed list to a client-readable string in the format "{item 1}, {item 2} and {item 3}"

    :param input_list: A list of items
    :return: A a client-readable string representing the passed list.
    """
    output_list = None

    if len(input_list) > 1:
        return ", ".join(input_list[:-1]) + f" and {input_list[-1]}"
    elif len(input_list) == 1:
        return input_list[0]
    
def __process_template_output(output_text):
    """
    Processes template output object and returns a version of it that is suitable for use in the output file. Please use this function to wrap any data that is intended to be rendered in the output document.

    :param output_text: An object to be used to render the output file.
    :return: A version of the passed object that has been processed and is suitable for use in the output file.
    """
    if isinstance(output_text, RichText):
        return __process_richtext(output_text)  # passes RichText objects off to their own designated processor
    else:
        if isinstance(output_text, float) and np.isnan(output_text):
            return ""   # catches NaN values, which are still rendered by docxtpl
        else:
            return output_text

def __process_richtext(rt):
    """
    Processes a RichText object and returns a version of it that is suitable for use in the output file. Please use this function to wrap a RichText object whenever returning it for use in the output document.

    :param rt: A RichText object.
    :return: A version of the RichText object (or a string object, if applicable) that is suitable for use in the output file.
    """
    if utility.richtext_is_empty(rt):
        return ""   # returns an empty string, as empty RichText objects (i.e., data never added to them) will still render within the output file
    else:
        return rt
