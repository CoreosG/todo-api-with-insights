```mermaid
graph TD
       Client --> AG[API Gateway + Cognito]
       AG -->|POST| SQS
       AG -->|GET/PUT/DEL| L1[Lambda Sync]
       L1 --> CW[CloudWatch Logs]
       L1 --> |Metrics|CWM 
       CW --> FH[Firehose]
       FH --> |Metrics|CWM
       FH --> S3B[S3 Bronze]
       L1 --> DDB[DynamoDB]
       AG -->|Metrics| CWM[CloudWatch Metrics]
       SQS -->|Poll| L2[Lambda Async]
       L2 --> CW
       L2 --> |Metrics|CWM  
       CW --> FH
       L2 --> DDB
       DDB --> |Metrics|CWM
       DDB --> DS[DynamoDB Streams]
       DS --> |Metrics|CWM
       DS --> L3[Lambda CDC]
       L3 --> FH
       L3 --> |Metrics|CWM
       FH --> S3B
       S3B --> GC[Glue Catalog/Crawler]
       GC --> |Metrics|CWM
       GC --> GS[S3 Silver via Glue Job]
       GS --> |Metrics|CWM
       GS --> A
       A[Athena] -->|Metrics| CWM
       A --> GG[S3 Gold]
       CWM -->|Dashboard/Alarms| CWM