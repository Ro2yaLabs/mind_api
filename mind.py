import argparse
import json
import pandas as pd
import os
from typing import List, Dict
import sqlite3

def mind(response):
    client_id = response.client_id
    user_responses = response.user_responses
    path = response.sqlite_database
    connection = sqlite3.connect(path)

    try:
        def read_table(table_name):
            query = f"SELECT * FROM {table_name}"
            df = pd.read_sql_query(query, connection)
            return df

        df_ids = read_table("IDs")
        df_prs = read_table("PRS")
        df_vak = read_table("VAK")
        df_emq = read_table("EMQ")
        df_trs = read_table("TRS")
        df_ctd = read_table("CTD")
        df_cmf = read_table("CMF")
        df_qtm = read_table("QTM")

        scoring_methods = {
        "A1": {1: 1, 2: 2, 3: 3, 4: 4},
        "A2": {1: 4, 2: 3, 3: 2, 4: 1},
        "A3": {1: 1, 2: 4, 3: 4, 4: 1},
        "A4": {1: 4, 2: 1, 3: 1, 4: 4}}

        traits = ["EI", "SN", "TF", "JP"]

        trait_results = {trait: [] for trait in traits}
        trait_letters = {}

        personality = {}

        for trait in traits:
            y_indices = set(df_prs[df_prs[trait] == "Y"]["Idx"].tolist())
            trait_responses = [response for idx, response in enumerate(user_responses) if idx + 1 in y_indices]
            count_1_or_2, count_3_or_4 = 0, 0
            for i in trait_responses:
                if i in (1, 2):
                    count_1_or_2 += 1
                else:
                    count_3_or_4 += 1

            probability_e = count_1_or_2 / max(1, len(trait_responses))
            probability_i = count_3_or_4 / max(1, len(trait_responses))
            
            personality[trait[0]] = round(probability_e, 2)*100
            personality[trait[1]] = round(probability_i, 2)*100

            if probability_e > probability_i:
                determined_trait = "E"
            else:
                determined_trait = "I"

            trait_letter = trait[0] if determined_trait == "E" else trait[1]
            trait_letters[trait] = trait_letter

        personality_type = "".join([trait_letters[trait] for trait in traits])
        personality["title"] = personality_type
        
        v_score, a_score, k_score = 0, 0, 0

        for idx, response in enumerate(user_responses):

            v_value, a_value, k_value = df_vak.loc[idx, ["V", "A", "K"]]

            if response in [3, 4]:
                v_score += 1
                a_score += 1
                k_score += 1
            elif response in [1, 2]:
                a_value += 1
                k_value += 1

        total = v_score + a_score + k_score
        Visual, Auditory, Kinesthetic = round(v_score/total*100, 2), round(a_score/total*100, 2), round((k_score)/total*100, 2)

        type = "Visual" if Auditory<Visual>Kinesthetic else "Auditory" if Visual<Auditory>Kinesthetic else "Kinesthetic"

        vak = {
            "type": type,
            "visual": Visual,
            "auditory": Auditory,
            "kinesthetic": Kinesthetic
        }
        
        scores_emq = {"SelfAwarness": 0, "ManagingEmotions": 0, "MotivatingOneself": 0, "Empathy": 0, "SocialSkills": 0}
        for idx, row in df_emq.iterrows():
            response = user_responses[idx]

            for category in scores_emq.keys():
                scoring_method = row[category]
                if pd.notna(scoring_method) and scoring_method != "":
                    scores_emq[category] += scoring_methods[scoring_method][response]


        ei = {
            "SelfAwarness": scores_emq["SelfAwarness"],
            "ManagingEmotions": scores_emq["ManagingEmotions"],
            "MotivatingOneself": scores_emq["MotivatingOneself"],
            "Empathy": scores_emq["Empathy"],
            "SocialSkills": scores_emq["SocialSkills"]
        }

        roles = {
            "RI": "Resource Investigator",
            "CO": "Co-ordinator",
            "PL": "Plant",
            "SH": "Shaper",
            "ME": "Monitor Evaluator",
            "IMP": "Implementer",
            "TW": "Teamworker",
            "CF": "Completer Finisher",
            "SP": "Specialist"
        }

        scores_trs = {role: 0 for role in roles.keys()}

        for idx, row in df_trs.iterrows():
            response = user_responses[idx]

            for role in scores_trs.keys():
                scoring_method = row[role]
                if pd.notna(scoring_method) and scoring_method != "":
                    scores_trs[role] += scoring_methods[scoring_method][response]

        rls = scores_trs
        scores_ctd = {col: 0 for col in df_ctd.columns if col != "Idx"}

        for idx, row in df_ctd.iterrows():
            response = user_responses[idx]

            for skill, scoring_method in row.items():
                if pd.notna(scoring_method) and scoring_method != "" and scoring_method in scoring_methods:
                    scores_ctd[skill] += scoring_methods[scoring_method][response]

        scores_qtm = {trait: 0 for trait in df_qtm.columns if trait != "Idx"}

        for idx, row in df_qtm.iterrows():
            response = user_responses[idx]

            for trait, scoring_method in row.items():
                if pd.notna(scoring_method) and scoring_method != "" and scoring_method in scoring_methods:
                    scores_qtm[trait] += scoring_methods[scoring_method][response]

        def determine_trait_level(score):
            if score > 15:
                return "balanced"
            elif 10 <= score <= 15:
                return "rebalanced"
            else:
                return "unbalanced"

        traits = []
        for trait, score in scores_qtm.items():
            try:
                id = df_ids.loc[df_ids['Title'] == trait]['Geo_Id'].values[0]
            except:
                pass
            traits.append({"id": id, "name": trait, "score":score, "level": determine_trait_level(score)})

        # The CTD Section
        def determine_skill_level(score):
            if score >= 30:
                return "Strong Skill"
            elif 25 <= score < 30:
                return "Needs Attention"
            else:
                return "Development Priority"

        def determine_aspect_level(score, num_skills):
            max_score = 36 if num_skills == 3 else 48
            percentage = (score / max_score) * 100
            if percentage >= 81:
                return "Advanced", percentage
            elif 58 <= percentage < 81:
                return "Intermediate", percentage
            else:
                return "Beginner", percentage

        def determine_space_level(score, num_aspects):
            max_score = {3: 108, 4: 144, 5: 180}
            percentage = (score / max_score[num_aspects]) * 100
            if percentage >= 72:
                return "Advanced", percentage
            elif 54 <= percentage < 72:
                return "Intermediate", percentage
            else:
                return "Beginner", percentage
            
        hierarchical_mapping = {}
        for _, row in df_cmf.iterrows():
            space, aspect, skill = row
            if space not in hierarchical_mapping:
                hierarchical_mapping[space] = {}
            if aspect not in hierarchical_mapping[space]:
                hierarchical_mapping[space][aspect] = []
            hierarchical_mapping[space][aspect].append(skill)
        hierarchical_mapping.pop('Space', None)

        scores = {col: 0 for col in df_ctd.columns if col != "Idx"}
        for idx, row in df_ctd.iterrows():
            response = user_responses[idx]
            for skill, scoring_method in row.items():
                if pd.isna(scoring_method) or scoring_method not in scoring_methods:
                    continue
                scores[skill] += scoring_methods[scoring_method][response]

        # Aggregate scores for each aspect and space
        space_scores = []
        for space, aspects in hierarchical_mapping.items():
            space_score = 0
            space_data = {}
            aspect_scores = []
            try:
                space_id = df_ids.loc[df_ids['Title'] == space]['Geo_Id'].values[0]
            except:
                pass
            for aspect, skills_list in aspects.items():
                aspect_score = sum(scores[skill] for skill in skills_list if skill in scores)
                space_score += aspect_score
                skills_data = {skill: (scores[skill], determine_skill_level(scores[skill])) for skill in skills_list if
                            skill in scores}
                try:
                    aspect_id = df_ids.loc[df_ids['Title'] == aspect]['Geo_Id'].values[0]
                except:
                    pass
                skill_scores = []
                for skill, skill_data in skills_data.items():
                    try:
                        skill_id = df_ids.loc[df_ids['Title'] == skill]['Geo_Id'].values[0]
                    except:
                        pass
                    skill_scores.append({"aspect_id": aspect_id, "skill_id": skill_id, "skill_name": skill, "score": skill_data[0], "level": skill_data[1]})

                level, percentage = determine_aspect_level(aspect_score, len(skills_list))
                aspect_scores.append({"space_id": space_id, "aspect_id": aspect_id, "aspect_name": aspect, "level": level, "percentage": round(percentage, 2), "skills": skill_scores})
            
            level, percentage = determine_space_level(space_score, len(aspects))
            space_scores.append({"space_id": space_id, "space_name": space, "level": level, "percentage": round(percentage, 2), "aspects": aspect_scores})

        # Create a dictionary to store the relationship between Space, Aspect, and Skill (JSON)
        space_aspect_skill_mapping = {}
        for space, aspects in hierarchical_mapping.items():
            space_data = {"level": None, "percentage": None, "aspects": {}}
            
            for aspect, skills_list in aspects.items():
                aspect_score = sum(scores[skill] for skill in skills_list if skill in scores)
                level, percentage = determine_aspect_level(aspect_score, len(skills_list))
                skills_data = {skill: {"score": scores[skill], "level": determine_skill_level(scores[skill])} for skill in skills_list if skill in scores}
                
                space_data["aspects"][aspect] = {
                    "Score": aspect_score,
                    "Level": level,
                    "Percentage": round(percentage, 2),
                    "Skills": skills_data
                }
            
            space_score = sum(space_data["aspects"][aspect]["Score"] for aspect in space_data["aspects"])
            space_data["level"], space_data["percentage"] = determine_space_level(space_score, len(space_data["aspects"]))
            
            space_aspect_skill_mapping[space] = space_data

        # Just in case we needed the JSON output
        assessment_json = {
            "client_id": client_id,
            "Personality_Type": personality,
            "vak": vak,
            "Emotional_Intelligance": ei,
            "Roles":rls,
            "Traits": traits,
            "Spaces": space_scores,
        }

    finally:
        connection.close()

    return assessment_json
