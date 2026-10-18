## 01-intro
When an agent forgets, the whole team starts over. Engram Collective gives agents a shared memory, a visible chain of evidence, and a way to carry work forward.

## 02-team
A coordinator plans the work. Researchers and builders can run in parallel. Verifiers test the actual artifacts, while a curator turns completed work into useful knowledge. Handoffs carry evidence, files and remaining work.

## 03-memory
Episodes preserve what happened. Semantic memory keeps sourced facts and corrections. Procedural memory stores tools and verified workflows. Engram combines pinned context, a recent memory cache and graph retrieval, while Mem zero extracts and refines facts.

## 04-causal
A corrected fact is more than a new sentence. Engram follows the tasks that depended on the old fact, marks their results stale, and links a revised plan to the new evidence. The causal timeline makes that change inspectable.

## 05-conflicts
When agents disagree, both claims survive. Each keeps its source and observation time. The resolver selects the latest active evidence under an explicit policy. Contradictory claims at the same timestamp remain unresolved, instead of becoming false certainty.

## 06-procedures
A reusable procedure is bound to exact artifact versions, preconditions and passing source checks. A different verifier must execute its own tests before activation. Reuse runs check those same files and record actual model usage and execution savings.

## 07-security
Every tenant has a separate graph. Memory can belong to a team, a user or an agent. Code runs in isolated Docker sandboxes with no network, a read only root and resource limits. Safeguard judges memory admission; it does not grant tool permissions.

## 08-restart
Postgres preserves conversations, task state and checkpoints. FalkorDB keeps relationships and causal dependencies. Qdrant supports Mem zero, with local embeddings for retrieval. Across separate live and infrastructure fixtures, restart checks preserved sessions, artifact files and checkpoints.

## 09-close
This is Engram Collective: an agent team designed to remember, coordinate and show its work. This walkthrough combines real app captures and infrastructure validation. The complete Qwen team run remains blocked by daily token quota.
