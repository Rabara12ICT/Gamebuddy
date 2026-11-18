import asyncio

# Pygbag discovers browser packages from imports in this entry point.
import pygame
import game


asyncio.run(game.main())
