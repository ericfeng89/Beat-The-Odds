mydata <- read.csv("testing.csv")
View(mydata)

model1 <- lm(mydata$price~mydata$bedrooms+mydata$bathrooms+mydata$Acres+mydata$floors+mydata$floors+mydata$waterfront+mydata$view+mydata$grade+mydata$sqft_above+mydata$sqft_basement+mydata$yr_built)

summary(model1)

model2 <- lm(mydata$price~mydata$bedrooms+mydata$bathrooms+mydata$Acres+mydata$waterfront+mydata$view+mydata$grade+mydata$sqft_above+I(mydata$sqft_above*mydata$sqft_above)+mydata$sqft_basement+mydata$yr_built)

summary(model2)
