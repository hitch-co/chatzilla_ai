import json
import hashlib

from google.api_core.exceptions import GoogleAPIError
from classes.ConfigManagerClass import ConfigManager
from my_modules import my_logging

runtime_debug_level = 'INFO'

class BQUploader:
    def __init__(self, bq_client):
        self.logger = my_logging.create_logger(
            dirname='log', 
            logger_name='BQUploader',
            debug_level=runtime_debug_level,
            mode='w',
            stream_logs=True
            )
        self.config = ConfigManager.get_instance()
        self.bq_client = bq_client

    def fetch_interaction_stats_as_text(self, table_id):
        # Construct a query to count occurrences of specific commands in a case-insensitive manner
        query = f"""
        SELECT
            SUM(CASE WHEN LOWER(content) LIKE '!chat%' THEN 1 ELSE 0 END) as chat_count,
            SUM(CASE WHEN LOWER(content) LIKE '!startstory%' THEN 1 ELSE 0 END) as startstory_count,
            SUM(CASE WHEN LOWER(content) LIKE '!addtostory%' THEN 1 ELSE 0 END) as addtostory_count,
            SUM(CASE WHEN LOWER(content) LIKE '!what%' THEN 1 ELSE 0 END) as what_count,
            SUM(CASE WHEN LOWER(content) LIKE '!factcheck%' THEN 1 ELSE 0 END) as factcheck_count,
            SUM(CASE WHEN LOWER(content) LIKE '!vc%' THEN 1 ELSE 0 END) as vibecheck_count,
            SUM(CASE WHEN LOWER(content) LIKE '@{self.config.twitch_bot_display_name}%' THEN 1 ELSE 0 END) as bot_shoutouts,
            COUNT(*) as total_messages              
        
        FROM `{table_id}`
        """

        # Execute the query and fetch the result
        try:
            result = self.bq_client.query(query).result()
            self.logger.debug(f"Result (type: {type(result)}): {result}")
        except GoogleAPIError as e:
            self.logger.error(f"BigQuery query failed: {e}")
            return None

        # Convert RowIterator to a list and get the first row
        result_list = list(result)[0]  # 'result' is the RowIterator from BQ query
        
        #Include line breaks in the stats text
        if result_list:
            stats_text = f"""
                Historic !commands usage and mentions: \n
                Total messages received: {result_list.total_messages} ||
                {self.config.twitch_bot_display_name} mentions: {result_list.bot_shoutouts}\n ||
                !chat: {result_list.chat_count}\n ||
                !startstory: {result_list.startstory_count}\n ||
                !what: {result_list.what_count}\n ||
                !factcheck: {result_list.factcheck_count}\n ||
                !vc (vibe check): {result_list.vibecheck_count}\n
                """

        # Log the formatted stats
        self.logger.debug(f"Formatted Stats: {stats_text}")
        return stats_text

    def fetch_unique_usernames_from_bq_as_list(self) -> list[str]:
        table_id = self.config.talkzillaai_userdata_table_id
        
        query = f"""
            SELECT DISTINCT user_name FROM `{table_id}`
            """

        # Execute the query
        query_job = self.bq_client.query(query)

        # Process the results
        results = [row.user_name for row in query_job]

        return results

    def fetch_user_chat_history_from_bq(
        self, 
        interactions_table_id: str, 
        users_table_id: str, 
        limit: int = 750,
        user_login: str = None, 
        content_filter: str = None
        ) -> list[dict]:
    
        if not content_filter:
            content_filter = '1=1'
        else :
            content_filter = f"lower(ui.content) LIKE '%{content_filter.lower()}%'"

        if not user_login:
            user_filter = '1=1'
        else:
            user_filter = f"lower(u.user_login) = lower('{user_login}')"
            
        str_results = []
        query = f"""
            SELECT
                CAST(ui.timestamp as string) as timestamp,
                u.user_login,
                ui.content,
                ui.message_id
            FROM `{interactions_table_id}` ui
            JOIN `{users_table_id}` u ON ui.user_id = u.user_id
            WHERE 1=1
                AND {user_filter}
                AND {content_filter}
            ORDER BY ui.timestamp DESC
            LIMIT {limit}
            """ 
        query_job = self.bq_client.query(query)
        str_results = [{
            "timestamp": row.timestamp, 
            "user_login": row.user_login, 
            "content": row.content,
            "message_id": row.message_id
            } for row in query_job]

        self.logger.debug(f"type of str_results: {type(str_results)}")
        return str_results

    def generate_twitch_user_interactions_records_for_bq(self, records: list[dict]) -> list[dict]:
        rows_to_insert = []
        for record in records:
            user_id = record.get('user_id')
            channel = record.get('channel')
            content = record.get('content')
            message_id = record.get('message_id')
            timestamp = record.get('timestamp')
            user_badges = record.get('badges')
            color = record.get('tags').get('color', '') if record.get('tags') else ''
            interaction_type = record.get('interaction_type')
            
            # message_id = self.generate_message_id(
            #     channel=channel, 
            #     user_id=user_id, 
            #     timestamp=timestamp, 
            #     content=content
            # )
            
            row = {
                "user_id": user_id,
                "channel": channel,
                "content": content,
                "timestamp": timestamp,
                "user_badges": user_badges,
                "color": color,
                "interaction_type": interaction_type,
                "message_id": message_id            
            }
            rows_to_insert.append(row)

        self.logger.debug("These are the user interactions records (rows_to_insert):")
        self.logger.debug(rows_to_insert[0:2])
        return rows_to_insert

    def send_recordsjob_to_bq(self, table_id, records:list[dict]) -> None:
        table = self.bq_client.get_table(table_id)
        try:
            errors = self.bq_client.insert_rows_json(table, records)     
        except GoogleAPIError as e:
            self.logger.error(f"BigQuery insert_rows_json failed: {e}")
            return

        if errors:
            self.logger.error(f"Encountered errors while inserting rows: {errors}")
            self.logger.error("These are the original records, in full:")
            self.logger.error(records)
        else:
            self.logger.info(f"BigQuery send_recordsjob_to_bq() job sent {len(records)} records successfully into table_id: {table_id}")
            self.logger.debug("These are the records:")
            self.logger.debug(records[0:2])
          
    def execute_query_on_bigquery(self, query):
        try:
            self.logger.info("Starting BigQuery execute_query_on_bigquery() job...")
            query_job = self.bq_client.query(query)

            self.logger.debug(f"Executing query...")
            query_job.result()

            self.logger.info(f"Query job {query_job.job_id} completed successfully.")

        except GoogleAPIError as e:
            self.logger.error(f"BigQuery job failed: {e}")

        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {e}")

        else:
            # Optionally, get and log job statistics
            job_stats = query_job.query_plan
            self.logger.debug(f"Query plan: {job_stats}")

if __name__ == '__main__':

    from google.cloud import bigquery
    import dotenv
    import os
    from classes.ConfigManagerClass import ConfigManager

    dotenv_load_result = dotenv.load_dotenv(dotenv_path='./config/.env')
    print(f"yaml_filepath: {os.getenv('CHATZILLA_CONFIG_YAML_FILEPATH')} (type: {type(os.getenv('CHATZILLA_CONFIG_YAML_FILEPATH'))})")
    ConfigManager.initialize(yaml_filepath=os.getenv('CHATZILLA_CONFIG_YAML_FILEPATH'))
    config = ConfigManager.get_instance()
    
    bq_client = bigquery.Client()

    chatdataclass = BQUploader(bq_client)

    # Test the fetch_user_chat_history_from_bq method
    test_list_of_chat_history_json = chatdataclass.fetch_user_chat_history_from_bq(
        user_login='mynameiskhan1090', 
        interactions_table_id='eh-talkzilla-ai.TalkzillaAI_UserData.user_interactions',
        users_table_id='eh-talkzilla-ai.TalkzillaAI_UserData.users', 
        limit=15
        )    
    print(test_list_of_chat_history_json)