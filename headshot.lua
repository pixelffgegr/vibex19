function logText(text)
                            print("[SERVER]: "..text)
                        end
                        local Player = game.Players:CreateLocalPlayer(0)
                        Player.CharacterAppearance = ""
                        Player:LoadCharacter(false)
                        logText("Let's check the player...")
                        local Character = Player.Character or Player.CharacterAdded:Wait()
                        for i, v in pairs(Character:GetChildren()) do
                            logText(tostring(v))
                            for i, w in pairs(v:GetChildren()) do
                                logText(tostring(v).." >> "..tostring(w))
                            end
                        end
						
			Player.Character["Right Arm"].BrickColor = BrickColor.new(24)
			Player.Character["Left Arm"].BrickColor = BrickColor.new(24)
			Player.Character["Head"].BrickColor = BrickColor.new(24)
			Player.Character["Torso"].BrickColor = BrickColor.new(23)
			Player.Character["Right Leg"].BrickColor = BrickColor.new(37)
			Player.Character["Left Leg"].BrickColor = BrickColor.new(37)
                        
                        local FOV = 30
                        local AngleOffsetX = 0
                        local AngleOffsetY = 0
                        local AngleOffsetZ = 0

                        local CameraAngle = Player.Character.Head.CFrame * CFrame.new(AngleOffsetX, AngleOffsetY, AngleOffsetZ)
                        local CameraPosition = Player.Character.Head.CFrame + Vector3.new(0, 0, 0) + (CFrame.Angles(0, -0.2, 0).lookVector.unit * 3)

                        local Camera = Instance.new("Camera", Player.Character)
                        Camera.Name = "ThumbnailCamera"
                        Camera.CameraType = Enum.CameraType.Scriptable
                        
                        Camera.CoordinateFrame = CFrame.new(CameraPosition.p, CameraAngle.p)
                        Camera.FieldOfView = FOV
                        workspace.CurrentCamera = Camera
                        logText("Rendering..")
			print("\nhere is your render!!!!!!!!!!!!\n")
                        print(game:service("ThumbnailGenerator"):click("PNG", 256, 256, true))
			print("\nDone!\n")