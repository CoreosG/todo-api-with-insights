Essa pasta tem prompts das tentativas falhas (feitas sabendo que não ia funcionar), comecei o projeto e queria pelo menos ver um exemplo de uma implementação funcionando antes de tentar eu mesmo, forcei uso de plan mode + agent e apenas aceitar codigo cegamente. (vibe code total hahaha, mas eu nunca tinha usado cursor antes, todos os meus projetos anteriores no trabalho no máximo tirei algumas dúvidas de como algo funciona, foi interessante o processo de aprender a usar essa ferramenta porque descobri que se vc nao fornece um pseudocodigo/stub no prompt a chance da cagada ser certa é alta)

Resultado final?
joguei tudo menos as ADRs fora (fiz boa parte manualmente mas pedi pro agent reestruturar em um .md bonito e acabou acrescentando tabelas etc) e reestruturei a arquitetura do sistema para simplificar o processo, tentei usar mais recursos da AWS para ja ter uma familiaridade com eles mas  vi que nao ia dar certo, então simplifiquei um pouco.

Coloquei todo historico dos chats que foram pro lixo, mas nao significa que nao aprendi nada, o resultado final que está vendo foi construido com base em alguns conhecimentos que obtive nessas tentativas falhas, como por exemplo: como desenvolver uma API corretamente, como alguns frameworks funcionam, como se organizar no desenvolvimento da API (quais camadas começar a desenvolver primeiro, o que configurar antes do desenvolvimento).
Não vou mentir, no resultado final não usei muitos prompts nas camadas de modelo, repositorio, serviço.
mas usei bastante até em controllers e entrypoint, pois julguei que com todo contexto das camadas anteriores o agente conseguiria fazer um bom trabalho criando estes arquivos.
no final tive que refatorar, modificar bastante coisa pra deixar o código pronto para teste local e em prod (deploy), tive muita dificuldade com IaC então tentei deixar o agent fazer um deploy funcional para analisar como isso funciona, resultado? nada funcionou kkkkkk, pelo  menos tenho uma ideia do que fazer com CDK e tentarei implementar passo a passo.

usei muito tab-completion nessa tentativa, a lógica foi: 
eu escrevia um comentário do que a função é/faz, exemplo: # Create pydantic models for user, *context*
o que é context? eu copiava e colava da ADR o que foi definido ou dava uma breve descrição do que pertence ali ou exemplo de código (maioria dos casos), então aceitava o auto complete.
Sem o auto complete com certeza eu não teria feito isso nesse prazo, ate aprender cada framework/lib eu estaria lascado. Felizmente pseudocodigo + llm = funções funcionais.
usei bastante o ask mode para validar o código que escrevi, apontar falhas de syntaxe, lógica. E depois revalidei cada analise em alguma I.A fora do cursor com outras duvidas do por que tenho que mudar tal coisa.
usei bastante o ask mode também para reescrever textos, lógicas nos arquivos.
usei o claude/grok para refinar alguns dos meus prompts, os prompts mais refinados foram feitos com ajuda deles, geralmente eu escrevo tudo como está aqui agora e peço para alguma I.a melhorar, como por exemplo esse proprio arquivo abaixo:

# Relatório de Desenvolvimento do Projeto

Este `README.md` detalha o processo de desenvolvimento e as lições aprendidas neste projeto, incluindo as abordagens iniciais mal-sucedidas e a estrutura final adotada.

## 1. Contexto e Tentativas Iniciais

A pasta contém o histórico de **tentativas iniciais e falhas** de implementação.

**Abordagem Inicial:**
* A motivação inicial era de obter um exemplo funcional rapidamente, priorizando a visualização de uma implementação completa antes da construção própria.
* Houve um uso excessivo e forçado dos modos `plan mode` e `agent`, com aceitação cega do código gerado.

**Resultado:**
* A arquitetura inicial foi descartada, com exceção dos documentos de Decisão de Arquitetura (ADRs).
* O sistema foi reestruturado e simplificado.
* Houve uma tentativa de maximizar o uso de recursos da AWS para familiarização, mas esta abordagem foi posteriormente simplificada por não ser viável na fase inicial.

## 2. Aprendizados das Falhas

O histórico dos *chats* descartados não representa um esforço perdido. O conhecimento adquirido nessas tentativas foi fundamental para a construção do resultado final, destacando-se:

* Como desenvolver uma API de forma correta e estruturada.
* O funcionamento básico de *frameworks* e bibliotecas-chave.
* Melhor organização no desenvolvimento de API, incluindo a ordem de desenvolvimento das camadas e as configurações prévias necessárias.

## 3. Estratégia de Desenvolvimento Final

A implementação final adotou uma abordagem mais seletiva no uso de ferramentas de IA:

| Camada | Uso de Geração de Código (`prompts`/`agent`) | Justificativa |
| :--- | :--- | :--- |
| Modelos, Repositório, Serviço | Baixo/Mínimo | Priorização da lógica manual e *tab-completion* para garantia de precisão e entendimento fundamental. |
| **Controllers e Entrypoint** | **Alto/Significativo** | Com o contexto claro das camadas inferiores, o agente foi considerado capaz de montar de forma eficiente a estrutura de *controllers* e o ponto de entrada da aplicação. |

**Processo de Refatoração:**
* Apesar da ajuda do agente, foi necessária uma extensa refatoração e modificação manual para preparar o código para testes locais e *deploy* em produção.

## 4. Infraestrutura como Código (IaC)

* O *deploy* da aplicação representou uma dificuldade significativa (IaC).
* A tentativa de usar o agente para criar um *deploy* funcional resultou em falha.
* Embora a implementação não tenha sido bem-sucedida, o processo forneceu *insights* iniciais sobre o uso do AWS CDK. A meta é implementar o IaC de forma incremental e passo a passo.

## 5. Fluxo de Trabalho e Ferramentas Auxiliares

### Uso de *Tab-Completion*

A produtividade no prazo estipulado foi viabilizada pela combinação de pseudocódigo e *tab-completion*:

1.  Escrita de um comentário descrevendo a função, Exemplo: `# Create pydantic models for user, *context*`.
2.  Inclusão de contexto (definição da ADR, breve descrição, ou exemplos de código).
3.  Aceitação da sugestão do *auto-complete*.

**Fórmula:** Pseudocódigo + *Large Language Model* (LLM) = Funções Funcionais.

### Uso do `Ask Mode`

O `ask mode` foi empregado para:

* Validar o código escrito, identificando falhas de sintaxe e lógica.
* Reescrever trechos de texto e lógicas complexas nos arquivos.

### Validação Cruzada de Prompts

Para maximizar a eficácia dos *prompts* mais importantes, foi utilizada uma abordagem de validação externa:

* O código analisado foi revalidado em outras I.A. fora da plataforma principal.
* Ferramentas como Claude e Grok foram usadas para refinar e otimizar os *prompts* originais, partindo de descrições brutas (semelhantes ao texto introdutório deste `README`).


