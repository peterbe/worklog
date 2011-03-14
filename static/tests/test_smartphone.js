test("LengthDescriber, hours", function() {
   var r = LengthDescriber.describe_hours(1);
   equals("1 hour", r);
   var r = LengthDescriber.describe_hours(1.5);
   equals("1 hour 30 minutes", r);
});