if dirty {
			s, _ := ctx.Value(keySession).(*Session)
			id, _ := ctx.Value(keySessionID).(string)
			if s != nil && id != "" {
				if err := m.Save(id, s); err != nil {
					log.Printf("session save error: %v", err)
				}
			}
		}
	})
}