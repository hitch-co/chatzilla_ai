from google.api_core.exceptions import GoogleAPIError

from classes.ConfigManagerClass import ConfigManager

from my_modules import my_logging

runtime_debug_level = 'DEBUG'

class BQUploader:
    def __init__(self, bq_client):
        #logger
        self.logger = my_logging.create_logger(
            dirname='log', 
            logger_name='BQUploader',
            debug_level=runtime_debug_level,
            mode='w',
            stream_logs=True
            )
        self.config = ConfigManager.get_instance()

        #Build the client
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
            SUM(CASE WHEN LOWER(content) LIKE '@chatzilla_ai%' THEN 1 ELSE 0 END) as chatzilla_shoutouts,
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
        if result_list:
            stats_text = f"""
                Historic !commands usage and mentions:
                Total messages received: {result_list.total_messages} ||
                @chatzilla_ai mentions: {result_list.chatzilla_shoutouts}\n ||
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

    def generate_twitch_user_interactions_records_for_bq(self, records: list[dict]) -> list[dict]:
        rows_to_insert = []
        for record in records:
            user_id = record.get('user_id')
            channel = record.get('channel')
            content = record.get('content')
            timestamp = record.get('timestamp')
            user_badges = record.get('badges')
            color = record.get('tags').get('color', '') if record.get('tags') else ''
            
            row = {
                "user_id": user_id,
                "channel": channel,
                "content": content,
                "timestamp": timestamp,
                "user_badges": user_badges,
                "color": color                
            }
            rows_to_insert.append(row)

        self.logger.debug("These are the user interactions records (rows_to_insert):")
        self.logger.debug(rows_to_insert[0:2])
        return rows_to_insert   

    def send_recordsjob_to_bq(self, table_id, records:list[dict]) -> None:

        self.logger.info("Starting BigQuery send_recordsjob_to_bq() job...")
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
            self.logger.info(f"{len(records)} records successfully inserted into table_id: {table_id}")
            self.logger.debug("These are the records:")
            self.logger.debug(records[0:2])
          
    def send_queryjob_to_bq(self, query):
        try:
            self.logger.info("Starting BigQuery send_queryjob_to_bq() job...")
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
    chatdataclass = BQUploader()
    chatdataclass._fetch_channel_viewers()