# Bootstrap do administrador

O endpoint `POST /setup/admin` não exige JWT e só cria a conta inicial. O primeiro pedido válido grava administrador e trilha de auditoria na mesma transação. Uma chave primária de bootstrap coordena chamadas simultâneas e evita inicializações paralelas. Depois de existir qualquer usuário, novas tentativas recebem `403`.

Exemplo do corpo:

```json
{"nome":"Admin","email":"admin@exemplo.com","senha":"SenhaForte#2026"}
```

O banco armazena hash bcrypt (custo 12), nunca a senha. A auditoria guarda instante, IP e user-agent. Não há segredo inicial ou senha padrão no repositório.

Para automação em um terminal protegido: `flask create-admin --email admin@exemplo.com`; o comando solicita a senha sem mostrá-la. Evite fornecer a senha como argumento de linha de comando, pois pode ficar no histórico do shell.
