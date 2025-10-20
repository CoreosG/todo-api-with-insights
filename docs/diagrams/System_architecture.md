```mermaid
graph TD
    Client --> AG[API Gateway + Cognito]
    
    %% API Layer
    AG -->|POST/GET/PUT/DEL| L1[Lambda Sync]
    AG -->|4XX/5XX Latency| CWM[CloudWatch Metrics]
    
    %% Sync Lambda Flow
    L1 --> DDB[DynamoDB]
    L1 --> CW[CloudWatch Logs]
    CW -->|Subscription Filter| FH[Firehose]
    FH --> S3B[S3 Bronze]
    
    %% CDC Flow
    DDB --> DS[DynamoDB Streams]
    DS --> L3[Lambda CDC]
    L3 --> CW
    CW --> FH
    L3 -->|RecordsProcessed| CWM
    FH --> S3B
    
    %% Data Lake
    S3B --> GC[Glue Catalog/Crawler]
    GC --> GS[S3 Silver<br/>Glue Job]
    GS --> A[Athena]
    A --> GG[S3 Gold]
    
    %% Observability Layer
    L1 -->|Duration Errors| CWM
    L3 -->|Duration Errors| CWM
    FH -->|IncomingBytes| CWM
    DDB -->|ConsumedRCU| CWM
    GC -->|CrawlerDuration| CWM
    GS -->|JobDuration| CWM
    A -->|BytesScanned| CWM
    
    %% Dashboard & Alarms
    CWM --> Dashboard[CloudWatch Dashboard]
    CWM --> Alarms[CloudWatch Alarms<br/>5xx>1/min<br/>Latency>500ms]
    
    %% Styling
    classDef api fill:#e1f5fe
    classDef data fill:#f3e5f5
    classDef obs fill:#e8f5e8
    classDef dlake fill:#fff3e0
    
    class AG,L1,L3 api
    class DDB,S3B,GC,GS,A,GG dlake
    class CW,FH,CWM,Alarms,Dashboard obs