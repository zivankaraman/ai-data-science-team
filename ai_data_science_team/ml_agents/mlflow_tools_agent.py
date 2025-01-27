
from typing import Any, Optional, Annotated, Sequence
import operator

import pandas as pd

from IPython.display import Markdown

from langchain_core.messages import BaseMessage, AIMessage

from langgraph.prebuilt import create_react_agent, ToolNode
from langgraph.prebuilt.chat_agent_executor import AgentState
from langgraph.graph import START, END, StateGraph

from ai_data_science_team.templates import BaseAgent
from ai_data_science_team.utils.regex import format_agent_name
from ai_data_science_team.tools.mlflow import (
    mlflow_search_experiments, 
    mlflow_search_runs,
    mlflow_create_experiment, 
    mlflow_predict_from_run_id,
    mlflow_launch_ui,
    mlflow_stop_ui,
    mlflow_list_artifacts,
    mlflow_download_artifacts,
    mlflow_list_registered_models,
    mlflow_search_registered_models,
    mlflow_get_model_version_details,
)

AGENT_NAME = "mlflow_tools_agent"

# TOOL SETUP
tools = [
    mlflow_search_experiments, 
    mlflow_search_runs, 
    mlflow_create_experiment, 
    mlflow_predict_from_run_id,
    mlflow_launch_ui,
    mlflow_stop_ui,
    mlflow_list_artifacts,
    mlflow_download_artifacts,
    mlflow_list_registered_models,
    mlflow_search_registered_models,
    mlflow_get_model_version_details,
]

class MLflowToolsAgent(BaseAgent):
    """
    An agent that can interact with MLflow by calling tools.
    
    Current tools include:
    - List Experiments
    - Search Runs
    - Create Experiment
    - Predict (from a Run ID)
    
    Parameters:
    ----------
    model : langchain.llms.base.LLM
        The language model used to generate the tool calling agent.
    mlfow_tracking_uri : str, optional
        The tracking URI for MLflow. Defaults to None.
    mlflow_registry_uri : str, optional
        The registry URI for MLflow. Defaults to None.
    **react_agent_kwargs : dict, optional
        Additional keyword arguments to pass to the agent's react agent.
    
    Methods:
    --------
    update_params(**kwargs):
        Updates the agent's parameters and rebuilds the compiled graph.
    ainvoke_agent(user_instructions: str=None, data_raw: pd.DataFrame=None, **kwargs):
        Asynchronously runs the agent with the given user instructions.
    invoke_agent(user_instructions: str=None, data_raw: pd.DataFrame=None, **kwargs):
        Runs the agent with the given user instructions.
    get_internal_messages(markdown: bool=False):
        Returns the internal messages from the agent's response.
    get_mlflow_artifacts(as_dataframe: bool=False):
        Returns the MLflow artifacts from the agent's response.
    get_ai_message(markdown: bool=False):
        Returns the AI message from the agent's response
    
    
    
    Examples:
    --------
    ```python
    from ai_data_science_team.ml_agents import MLflowToolsAgent
    
    mlflow_agent = MLflowToolsAgent(llm)

    mlflow_agent.invoke_agent(user_instructions="List the MLflow experiments")

    mlflow_agent.get_response()

    mlflow_agent.get_internal_messages(markdown=True)

    mlflow_agent.get_ai_message(markdown=True)

    mlflow_agent.get_mlflow_artifacts(as_dataframe=True)
    
    ```
    
    Returns
    -------
    MLflowToolsAgent : langchain.graphs.CompiledStateGraph 
        An instance of the MLflow Tools Agent.
    
    """
    
    def __init__(
        self, 
        model: Any,
        mlflow_tracking_uri: Optional[str]=None,
        mlflow_registry_uri: Optional[str]=None,
        **react_agent_kwargs,
    ):
        self._params = {
            "model": model,
            "mlflow_tracking_uri": mlflow_tracking_uri,
            "mlflow_registry_uri": mlflow_registry_uri,
            **react_agent_kwargs,
        }
        self._compiled_graph = self._make_compiled_graph()
        self.response = None
    
    def _make_compiled_graph(self):
        """
        Creates the compiled graph for the agent.
        """
        self.response = None
        return make_mlflow_tools_agent(**self._params)
    
    
    def update_params(self, **kwargs):
        """
        Updates the agent's parameters and rebuilds the compiled graph.
        """
        for k, v in kwargs.items():
            self._params[k] = v
        self._compiled_graph = self._make_compiled_graph()
        
    async def ainvoke_agent(
        self, 
        user_instructions: str=None, 
        data_raw: pd.DataFrame=None, 
        **kwargs
    ):
        """
        Runs the agent with the given user instructions.
        
        Parameters:
        ----------
        user_instructions : str, optional
            The user instructions to pass to the agent.
        data_raw : pd.DataFrame, optional
            The data to pass to the agent. Used for prediction and tool calls where data is required.
        kwargs : dict, optional
            Additional keyword arguments to pass to the agents ainvoke method.
        
        """
        response = await self._compiled_graph.ainvoke(
            {
                "user_instructions": user_instructions,
                "data_raw": data_raw.to_dict() if data_raw is not None else None,
            }, 
            **kwargs
        )
        self.response = response
        return None
    
    def invoke_agent(
        self, 
        user_instructions: str=None, 
        data_raw: pd.DataFrame=None, 
        **kwargs
    ):
        """
        Runs the agent with the given user instructions.
        
        Parameters:
        ----------
        user_instructions : str, optional
            The user instructions to pass to the agent.
        data_raw : pd.DataFrame, optional
            The raw data to pass to the agent. Used for prediction and tool calls where data is required.
        kwargs : dict, optional
            Additional keyword arguments to pass to the agents invoke method.
        
        """
        response = self._compiled_graph.invoke(
            {
                "user_instructions": user_instructions,
                "data_raw": data_raw.to_dict() if data_raw is not None else None,
            },
            **kwargs
        )
        self.response = response
        return None
    
    def get_internal_messages(self, markdown: bool=False):
        """
        Returns the internal messages from the agent's response.
        """
        pretty_print = "\n\n".join([f"### {msg.type.upper()}\n\nID: {msg.id}\n\nContent:\n\n{msg.content}" for msg in self.response["internal_messages"]])       
        if markdown:
            return Markdown(pretty_print)
        else:
            return self.response["internal_messages"]
    
    def get_mlflow_artifacts(self, as_dataframe: bool=False):
        """
        Returns the MLflow artifacts from the agent's response.
        """
        if as_dataframe:
            return pd.DataFrame(self.response["mlflow_artifacts"])
        else:
            return self.response["mlflow_artifacts"]
    
    def get_ai_message(self, markdown: bool=False):
        """
        Returns the AI message from the agent's response.
        """
        if markdown:
            return Markdown(self.response["messages"][0].content)
        else:
            return self.response["messages"][0].content
            
    
    

def make_mlflow_tools_agent(
    model: Any,
    mlflow_tracking_uri: str=None,
    mlflow_registry_uri: str=None,
    **react_agent_kwargs,
):
    """
    MLflow Tool Calling Agent
    """
    
    try:
        import mlflow
    except ImportError:
        return "MLflow is not installed. Please install it by running: !pip install mlflow"
    
    if mlflow_tracking_uri is not None:
        mlflow.set_tracking_uri(mlflow_tracking_uri)
    
    if mlflow_registry_uri is not None:
        mlflow.set_registry_uri(mlflow_registry_uri)
    
    class GraphState(AgentState):
        internal_messages: Annotated[Sequence[BaseMessage], operator.add]
        user_instructions: str
        data_raw: dict
        mlflow_artifacts: dict

    
    def mflfow_tools_agent(state):
        """
        Postprocesses the MLflow state, keeping only the last message
        and extracting the last tool artifact.
        """
        print(format_agent_name(AGENT_NAME))
        print("    * RUN REACT TOOL-CALLING AGENT")
        
        tool_node = ToolNode(
            tools=tools
        )
        
        mlflow_agent = create_react_agent(
            model, 
            tools=tool_node, 
            state_schema=GraphState,
            **react_agent_kwargs,
        )
        
        response = mlflow_agent.invoke(
            {
                "messages": [("user", state["user_instructions"])],
                "data_raw": state["data_raw"],
            },
        )
        
        print("    * POST-PROCESS RESULTS")

        internal_messages = response['messages']

        # Ensure there is at least one AI message
        if not internal_messages:
            return {
                "internal_messages": [],
                "mlflow_artifacts": None,
            }

        # Get the last AI message
        last_ai_message = AIMessage(internal_messages[-1].content, role = AGENT_NAME)

        # Get the last tool artifact safely
        last_tool_artifact = None
        if len(internal_messages) > 1:
            last_message = internal_messages[-2]  # Get second-to-last message
            if hasattr(last_message, "artifact"):  # Check if it has an "artifact"
                last_tool_artifact = last_message.artifact
            elif isinstance(last_message, dict) and "artifact" in last_message:
                last_tool_artifact = last_message["artifact"]

        return {
            "messages": [last_ai_message], 
            "internal_messages": internal_messages,
            "mlflow_artifacts": last_tool_artifact,
        }

    
    workflow = StateGraph(GraphState)
    
    workflow.add_node("mlflow_tools_agent", mflfow_tools_agent)
    
    workflow.add_edge(START, "mlflow_tools_agent")
    workflow.add_edge("mlflow_tools_agent", END)
    
    app = workflow.compile()

    return app
    