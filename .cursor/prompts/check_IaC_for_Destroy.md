# Prompts:


Prompt:

@infra/ check IaC code, is it properly DELETING EVERYTHING on destroy? i want it to leave 0 traces of what was deployed, no security compliance is  needed. empty s3 bucketts and everything else.

if you find something, fix it on the code then run cdk synth, do not alterate other parts of code.

Objective: ensure proper cdk destroy command, since it's a challenge i'll just make sure it deletes everything.

commit link: 0ce926876e9cf5073365056f1339b89fffb86479