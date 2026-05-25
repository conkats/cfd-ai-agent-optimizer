# CFD AI Agent Optimizer

An orchestrated multi-agent system for automated 2D aerodynamic shape optimization using [Code_Saturne](https://code-saturne.org/) (open-source CFD solver) and Claude AI models.

## Overview

This repository demonstrates a practical approach to **team-based AI agent orchestration** for engineering workflows. A specialized team of AI agents collaborates to execute a complete CFD shape optimization study, combining:

- **Claude Opus 4.7** for complex CFD problem solving and case setup
- **Claude Sonnet 4.6** for supporting tasks (code review, documentation)
- **Memory, MCP, and Tools integration** for stateful agent communication
- **Code_Saturne v9.0** for high-fidelity CFD simulations

## Quick Start

### 1. Enable Agent Teams

```bash
# Configure Claude for teammate mode
vi ~/.claude/settings.json

# Add this configuration
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

### 2. Launch Claude in Teammate Mode

```bash
claude --teammate-mode in-process
```

### 3. Initialize Agent Team

Select your preferred Claude model and paste the team prompt from `prompt-agent-shape.txt`:

```bash
cat prompt-agent-shape.txt
```

This creates a 5-agent team in the following sequence:

| Agent | Role | Model | Purpose |
|-------|------|-------|---------|
| **web-research-orchestrator** | Research Lead | Opus | Literature search & analysis of shape effects |
| **saturne-mesh-design** | Mesh Engineer | Opus | Generate parametric mesh scripts for 4 shapes |
| **cfd-case-runner** | Simulation Lead | Opus | Execute Code_Saturne cases for each shape |
| **descriptor** | Report Writer | Sonnet | Synthesize 2-page findings & usage guide |
| **code-reviewer** | Quality Assurance | Opus | Optimize & simplify generated scripts |

## Repository Structure

```
.
├── .claude/agents/              # Agent definitions
│   ├── cfd-case-runner.md      # CFD simulation orchestration
│   ├── code-reviewer.md        # Code quality & optimization
│   └── session-logger.md       # Session documentation
├── case_*/                      # CFD case directories (cylinder, triangle, square, half_cylinder)
│   ├── MESH/                   # Mesh generation files
│   ├── DATA/                   # Case setup (setup.xml, user source code)
│   ├── SRC/                    # C/C++ user routines
│   ├── RESU/                   # Simulation results
│   └── run.cfg                 # Code_Saturne configuration
├── scripts/                     # Utility scripts (mesh generation, post-processing)
├── results/                     # Analysis outputs & plots
├── report/                      # Generated reports
├── prompt-agent-shape.txt      # Team initialization prompt
├── smgr.xml                    # Code_Saturne study manager config
└── README.md
```

## Key Features

### Agent Coordination
- **Async handoff**: Each agent passes structured output to the next
- **Shared memory**: Session context preserved across agent teams
- **Tool integration**: Direct access to shell, file I/O, Python execution
- **Error recovery**: Built-in debugging & code review loops

### CFD Workflow
- **4-shape comparison**: Cylinder, triangle, square, half-cylinder
- **Aerodynamic metrics**: Drag, lift, pressure coefficient (Cp), velocity magnitude
- **Mesh parametrization**: Transfinite quad mesh via Gmsh (`cylinder_crossflow.py` template)
- **Batch execution**: Code_Saturne study manager for parametric sweeps
- **Post-processing**: Python/ParaView scripts for visualization

### Optimization Loop
1. **Generate** → Mesh design (parametric variation)
2. **Simulate** → Code_Saturne CFD runs
3. **Analyze** → Extract aerodynamic forces & coefficients
4. **Report** → Comparative findings + usage instructions
5. **Refine** → Code optimization & next iteration

## Working with Agents

### Running a Single Agent

```bash
# In Claude teammate mode, invoke an agent directly:
@cfd-case-runner Create and run a Code_Saturne case for cylinder flow at Re=100

@code-reviewer Review the mesh generation script for numerical stability

@descriptor Write a session log of today's work
```

### Chaining Agents

Agents automatically pass outputs when referenced:

```
cfd-case-runner:
  └─> (provides case setup)
        ↓
      code-reviewer:
        └─> (provides optimized config)
             ↓
           cfd-case-runner:
             └─> (executes refined case)
```

## Technology Stack

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.11+ | Mesh generation, post-processing |
| Code_Saturne | v9.0 | CFD solver |
| Gmsh | (via code_saturne) | Mesh generation |
| Claude API | Opus 4.7, Sonnet 4.6 | Agent intelligence |
| ParaView | (optional) | Visualization |

## Example: Optimize Cylinder Shape

```bash
# 1. Paste the team prompt to start orchestration
cat prompt-agent-shape.txt | pbcopy  # macOS
# or
cat prompt-agent-shape.txt | xclip -i  # Linux

# 2. In Claude teammate mode, initialize:
# "Create agent team to generate shape comparison report"

# 3. Agents execute automatically:
#    - Mesh designs for 4 shapes
#    - 4 separate CFD cases
#    - Converged simulations
#    - Optimized Python scripts
#    - 2-page findings report

# 4. Check results:
ls results/  # Plots & CSV data
cat report/  # Findings & methodology
```

## Language Composition

- **Python**: 41.4% (mesh generation, post-processing, orchestration)
- **C**: 32.9% (Code_Saturne internals)
- **C++**: 24.5% (Code_Saturne/user routines)
- **Shell**: 1.2% (build & runtime scripts)

## Key Agent Capabilities

### cfd-case-runner
- Interprets CFD problem specifications
- Creates Code_Saturne case directory structure
- Compiles user source code (C/C++)
- Executes single cases or parametric sweeps
- Monitors solver convergence & debugging

### code-reviewer
- Reviews Python, C, C++ code
- Physics & numerical correctness checks
- Code_Saturne API validation
- Performance & maintainability assessment

### descriptor
- Synthesizes session work into markdown logs
- Generates technical reports
- Tracks decisions, findings, & next steps

## Memory System

Each agent maintains persistent memory at:
```
.claude/agent-memory/
├── cfd-case-runner/    # CFD patterns, solver quirks, case templates
├── code-reviewer/      # Code style, domain-specific idioms
└── descriptor/         # Project milestones, workflow patterns
```

This builds institutional knowledge across sessions.

## License

GNU General Public License v3.0 — See [LICENSE](LICENSE) for details.

## References

- [Code_Saturne Documentation](https://code-saturne.org/): CFD solver guide
- [Claude API](https://claude.ai): Agent infrastructure
- [Gmsh](https://gmsh.info/): Mesh generation

## Author

**Constantinos Katsamis** (EDF Energy)

---

**Status**: Active development. Optimized for 2D shape studies; extensible to 3D and multi-objective workflows.
