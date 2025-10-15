# Prompt

First prompt:
Gustavo Rodrigues
8:15 AM (6 hours ago)
to me

It looks like this message is in Portuguese
BoM dia,

Do ponto de vista da API, nunca faça sua aplicação depender do onde ela vai funcionar, ou seja, ela usa entrypont, que pode ser um handle de um lambda ou pode ser o próprio server.

Avalie usar isso: 
https://pypi.org/project/mangum/

Assim sua aplicação  ainda que usando fastApi funcionaria tranquilamente num handle de lambda.

Outra questão importante, isso vale pra banco de dados também, considere usar repository pattern pra nao manter a lógica e basta ração de uso do banco de dados na controller, e a lógica em si, como algo vai fazer algo, use a camada de service.

Lógica deve ser

Entry point -> middleware (opcional) -> controller -> service -> Repository > database.


Assim vc consegue avançar na API e ter flexibilidade na decisão de um caminho ou outro.

Sobre usar lambda ou server, tem relação direta com o uso e característica da aplicação. Se tem muito request, muito processamento, ou processamento intensivo, e tem sensibilidade a cold start vai pra container, se é algo pequeno, direto, rápido, não precisa ficar rodando muito tempo, e vc pode escalar e não tem sensibilidade de coldstart vai de lambda.

No seu caso qualquer um dos dois é válido. Acho lambda mais fácil de configurar do que server.

Em server vc pode ir pra ECS, lightsail, app runner.


Compare the recommended structure on this email to my current project, see @000-architecture-overview.md, mermaid: System_architecture.md, api details: @004-api-framework.md.

he suggested a repository, what is it?


Objective:
Compare the proposed logic to my current developed logic, for the most part i think i did correctly, but i don't know what the repository in the recommendation is.

## Subsequent prompts

Prompt:
Generate prompt for the agent to update @004-api-framework.md to include the new decisions, use lambda layers to share code between lambdas, we'll use that for the  repository pattern abstraction, new logic for lambdas should be:
Handler (Entrypoint) -> Controller -> Service -> Repository (lambda layer) -> DynamoDB

Objective:
Get a elaborate prompt to update [004-api-framework](/docs/adrs/004-api-framework-and-architecture.md) with the new architecture decisions.