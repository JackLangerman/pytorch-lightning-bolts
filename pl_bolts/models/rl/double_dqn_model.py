"""
Double DQN
"""
import argparse
from collections import OrderedDict
from typing import Tuple

import pytorch_lightning as pl
import torch

from pl_bolts.losses.rl import double_dqn_loss
from pl_bolts.models.rl.dqn_model import DQN


class DoubleDQN(DQN):
    """
    Double Deep Q-network (DDQN)
    PyTorch Lightning implementation of `Double DQN <https://arxiv.org/pdf/1509.06461.pdf>`_

    Paper authors: Hado van Hasselt, Arthur Guez, David Silver

    Model implemented by:

        - `Donal Byrne <https://github.com/djbyrne>`

    Example:

        >>> from pl_bolts.models.rl.double_dqn_model import DoubleDQN
        ...
        >>> model = DoubleDQN("PongNoFrameskip-v4")

    Train::

        trainer = Trainer()
        trainer.fit(model)

    Args:
        env: gym environment tag
        gpus: number of gpus being used
        eps_start: starting value of epsilon for the epsilon-greedy exploration
        eps_end: final value of epsilon for the epsilon-greedy exploration
        eps_last_frame: the final frame in for the decrease of epsilon. At this frame espilon = eps_end
        sync_rate: the number of iterations between syncing up the target network with the train network
        gamma: discount factor
        lr: learning rate
        batch_size: size of minibatch pulled from the DataLoader
        replay_size: total capacity of the replay buffer
        warm_start_size: how many random steps through the environment to be carried out at the start of
            training to fill the buffer with a starting point
        sample_len: the number of samples to pull from the dataset iterator and feed to the DataLoader

    Note:
        This example is based on
        https://github.com/PacktPublishing/Deep-Reinforcement-Learning-Hands-On-Second-Edition/blob/master/Chapter08/03_dqn_double.py

    Note:
        Currently only supports CPU and single GPU training with `distributed_backend=dp`
    """

    def training_step(self, batch: Tuple[torch.Tensor, torch.Tensor], _) -> OrderedDict:
        """
        Carries out a single step through the environment to update the replay buffer.
        Then calculates loss based on the minibatch recieved
        Args:
            batch: current mini batch of replay data
            _: batch number, not used
        Returns:
            Training loss and log metrics
        """

        # calculates training loss
        loss = double_dqn_loss(batch, self.net, self.target_net)

        if self.trainer.use_dp or self.trainer.use_ddp2:
            loss = loss.unsqueeze(0)

        # Soft update of target network
        if self.global_step % self.sync_rate == 0:
            self.target_net.load_state_dict(self.net.state_dict())

        log = {
            "total_reward": self.total_rewards[-1],
            "avg_reward": self.avg_rewards,
            "train_loss": loss,
            # "episodes": self.total_episode_steps,
        }
        status = {
            "steps": self.global_step,
            "avg_reward": self.avg_rewards,
            "total_reward": self.total_rewards[-1],
            "episodes": self.done_episodes,
            # "episode_steps": self.episode_steps,
            "epsilon": self.agent.epsilon,
        }

        return OrderedDict(
            {
                "loss": loss,
                "avg_reward": self.avg_rewards,
                "log": log,
                "progress_bar": status,
            }
        )


def cli_main():
    parser = argparse.ArgumentParser(add_help=False)

    # trainer args
    parser = pl.Trainer.add_argparse_args(parser)

    # model args
    parser = DoubleDQN.add_model_specific_args(parser)
    args = parser.parse_args()

    model = DoubleDQN(**args.__dict__)

    trainer = pl.Trainer.from_argparse_args(args)
    trainer.fit(model)


if __name__ == '__main__':
    cli_main()
