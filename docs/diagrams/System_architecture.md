```mermaid
       graph TD
           Client --> AG[API Gateway + Cognito]
           AG -->|POST| SQS
           AG -->|GET/PUT/DEL| L1[Lambda Sync]
           L1 --> CW[CloudWatch Logs]
           CW --> FH[Firehose]
           FH --> |Metrics|CWM
           FH --> S3B[S3 Bronze]
           L1 --> DDB[DynamoDB]
           AG -->|Metrics| CWM[CloudWatch Metrics]
           SQS -->|Poll| L2[Lambda Async]
           L2 --> CW
           CW --> FH
           L2 --> DDB
           DDB --> DS[DynamoDB Streams]
           DS --> L3[Lambda CDC]
           L3 --> FH
           FH --> S3B
           S3B --> GC[Glue Catalog/Crawler]
           GC --> |Metrics|CWM
           GC --> GS[S3 Silver via Glue Job]
           GS --> A
           A[Athena] -->|Metrics| CWM
           A --> GG[S3 Gold]
           CWM -->|Dashboard/Alarms| CWM 