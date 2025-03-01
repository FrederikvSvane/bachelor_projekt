# Specific description of problem

### Clear version:

We define the court scheduling problem as follows:

**Inputs:**
* **Meetings** $M=\{m_1,\ldots,m_k\}$, each with a total duration $d(m)\in\mathbb{N}$ (in $G$-minute intervals).
* **Judges** $J=\{j_1,\ldots,j_n\}$.
* **Courtrooms** $R=\{r_1,\ldots,r_m\}$.
* **Days** $D\in\mathbb{N}$, daily minutes $D_m\in\mathbb{N}$, granularity $G\in\mathbb{N}$ (slots are $G$-minutes long).

**Time Slots:**
* Each day is divided into $\frac{D_m}{G}$ slots. All slots across $D$ days form the set:
  $$T=\{(d,t)\mid d\in[1,D],t\in[0,\frac{D_m}{G}-1]\}$$

**Appointment:**
* $A=(m,j,r,d,t_{start},l)$, where:
  * $m\in M$, $j\in J$, $r\in R$
  * $d\in[1,D]$, $t_{start}\in[0,\frac{D_m}{G}-1]$
  * $l\in\mathbb{N}$, such that $t_{start}+l\leq\frac{D_m}{G}$

**Schedule:**
* A set $S=\{A_1,\ldots,A_p\}$ assigning all parts of meetings to appointments.

**Validity:** $S$ is valid if:
1. **Coverage:**
   * For every $m\in M$, the sum of $duration$ across all appointments in $S$ for $m$ equals $d(m)$.
2. **No Overlaps:**
   * For any two distinct appointments $A_i,A_j\in S$, if their time intervals overlap (i.e., same $day$ and overlapping slots), then:
     * $j_i\neq j_j$ (different judges) **and** $r_i\neq r_j$ (different courtrooms).


The problem then becomes: given the named inputs, produce a valid schedule.

___

### Alternative, more coherent version:

We define the court scheduling problem as follows:

Given a set of meetings $M=\{m_1,\ldots,m_k\}$, judges $J=\{j_1,\ldots,j_n\}$, courtrooms $R=\{r_1,\ldots,r_m\}$, a number of work days $D\in\mathbb{N}$, the amount of minutes in each work day $D_m\in\mathbb{N}$, and a granularity $G\in\mathbb{N}$ specifying $G$-minute intervals. Each meeting $m$ has a total duration $d(m)\in\mathbb{N}$ measured in $G$-minute intervals.

Each day is divided into $D_m/G$ slots. The set of all time slots across all days is defined as:
$$T=\{(d,t)\mid d\in[1,D],t\in[0,D_m/G-1]\}$$

An appointment is defined as $A=(m,j,r,d,t_{start},l)$, where $m\in M$ is a meeting, $j\in J$ is a judge, $r\in R$ is a courtroom, $d\in[1,D]$ is the day, $t_{start}\in[0,D_m/G-1]$ is the starting time slot, and $l\in\mathbb{N}$ is the length such that $t_{start}+l\leq D_m/G$.

A schedule $S=\{A_1,\ldots,A_p\}$ assigns all meetings to appointments. A schedule $S$ is valid if and only if:

For every meeting $m\in M$, the sum of durations across all appointments in $S$ for $m$ equals $d(m)$. And for any two distinct appointments $A_i,A_j\in S$, if their time intervals overlap (meaning same day and overlapping slots), then they must have different judges $j_i\neq j_j$ and different courtrooms $r_i\neq r_j$.

The problem then becomes: given the named inputs, produce a valid schedule.